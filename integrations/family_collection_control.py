"""Opt-in report-role control of one preinstalled learner user target, never root."""
from pathlib import Path
import subprocess

UNIT = 'family-activitywatch.target'
SERVICES = ('family-aw-server.service', 'family-aw-watchers.service')


def control(config, operation, run=subprocess.run):
    if config.get('provider') != 'activitywatch' or config.get('allow_collection_control') is not True:
        raise ValueError('Collection control is not enrolled; review and enable it during learner setup')
    expected = {'op'} if operation.get('op') == 'collection-status' else {'op', 'enabled', 'acknowledge_raw_storage'}
    if set(operation) != expected or operation.get('op') not in ('collection-status', 'collection-set'):
        raise ValueError('Unsupported collection operation')
    if operation['op'] == 'collection-set':
        if type(operation['enabled']) is not bool or type(operation['acknowledge_raw_storage']) is not bool:
            raise ValueError('Expected explicit collection choices')
        if operation['enabled'] and operation['acknowledge_raw_storage'] is not True:
            raise ValueError('Acknowledge upstream raw URL/title storage before starting collection')
    # The installer/operator supplies the reviewed target and its watcher units.
    # No remote executable, unit, UID, environment, path or command is accepted.
    result = run(['/usr/bin/systemctl', '--user', 'show', UNIT,
                  '--property=LoadState', '--property=ActiveState', '--property=Wants'],
                 capture_output=True, text=True, check=True, timeout=5)
    state = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if state.get('LoadState') != 'loaded':
        return {'ready': False, 'state': 'not-installed', 'enabled': False,
                'message': 'Install and test the ActivityWatch target and its watcher services first'}
    if not set(SERVICES) <= set(state.get('Wants','').split()):
        raise ValueError('The ActivityWatch target does not supervise both required services')
    service_states=[]
    for unit in SERVICES:
        result=run(['/usr/bin/systemctl','--user','show',unit,'--property=LoadState','--property=ActiveState','--property=PartOf'],
                   capture_output=True,text=True,check=True,timeout=5)
        service=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
        if service.get('LoadState')!='loaded' or UNIT not in service.get('PartOf','').split():
            raise ValueError('Watcher/server service is not enrolled in the supervised target')
        service_states.append(service.get('ActiveState'))
    if operation['op'] == 'collection-set':
        run(['/usr/bin/systemctl', '--user', 'start' if operation['enabled'] else 'stop', UNIT],
            check=True, capture_output=True, text=True, timeout=10)
        return control(config, {'op': 'collection-status'}, run)
    active = state.get('ActiveState')
    enabled=active=='active' and all(value=='active' for value in service_states)
    if active=='active' and not enabled:active='incomplete'
    if active=='inactive' and any(value=='active' for value in service_states):active='incomplete'
    return {'ready': True, 'state': active or 'unknown', 'enabled': enabled,
            'message': 'Supervised ActivityWatch target status; not proof that every watcher is producing data'}
