"""Hermetic helper routing/relay tests; no network, graphical session or credentials."""
import contextlib
import io
import json
import os
import pathlib
import runpy
import subprocess
import sys
import tempfile
import time
from unittest import mock

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts/family-lab'


def context(home, cfg):
    home.mkdir()
    path = home / '.config/family-lab/config.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(cfg))
    with mock.patch.dict(os.environ, {'HOME': str(home)}):
        return runpy.run_path(str(SCRIPT), run_name='family_lab_test')


def rejects(function, *args):
    try:
        function(*args)
    except (ValueError, FileNotFoundError, subprocess.SubprocessError):
        return
    raise AssertionError('Expected rejection: ' + function.__name__)


with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
    root = pathlib.Path(directory)
    routes = {'mom': {'learner-a': 'family-mom-a-relay'}}
    dad = context(root / 'helper-a', {'view_aliases': {'learner-a': 'family-a-view'},
                                    'forward_routes': routes})
    mom_home = root / 'helper-b'
    mom = context(mom_home, {'view_aliases': {'learner-a': 'family-a-view'},
                            'relay_sources': {'dad': ['learner-a']},
                            'forward_routes': {'dad': {'learner-a': 'family-dad-a-relay'}}})
    learner = context(root / 'learner', {'notify_aliases': {'dad': 'family-dad-notify',
                                                          'mom': 'family-mom-notify'},
                                       'notify_alias': 'family-legacy-notify'})
    for entrypoint, arguments, expected in (
        ('ask-dad', ['hello'], 'family-dad-notify'),
        ('ask-mom', ['hello'], 'family-mom-notify'),
        ('family-lab', ['ask', 'mom', 'hello'], 'family-mom-notify'),
    ):
        calls = []
        with mock.patch.dict(learner['main'].__globals__, {'run': lambda argv, **kw: calls.append((argv, kw))}), \
                mock.patch.object(sys, 'argv', [entrypoint, *arguments]):
            learner['main']()
        assert calls[-1][0][-1] == expected
        assert json.loads(calls[-1][1]['input']) == {'message': 'hello'}
    cfg_path = root / 'learner/.config/family-lab/config.json'
    cfg_path.write_text(json.dumps({'notify_alias': 'family-legacy-notify'}))
    with mock.patch.object(sys, 'argv', ['ask-mom', 'hello']):
        rejects(learner['main'])  # Never silently deliver Mom requests to Dad.
    calls = []
    with mock.patch.dict(learner['main'].__globals__, {'run': lambda argv, **kw: calls.append(argv)}), \
            mock.patch.object(sys, 'argv', ['ask-dad', 'hello']):
        learner['main']()
    assert calls[-1][-1] == 'family-legacy-notify'

    created = time.time()
    request = {'id': 'a' * 32, 'person': 'learner-a', 'message': '<b>Help</b> $(touch NEVER)',
               'time': created, 'expires': created + 600}
    dad['enqueue_help'](request, 'learner-a')
    assert dad['forward_choices'](request, dad['config']()) == {'Ask Mom': 'mom'}
    mom_env = dict(os.environ, HOME=str(mom_home))
    wire_payloads = []
    def receiver(source, peer, payload):
        return subprocess.run(['python3', str(SCRIPT), 'receive-forward', source, peer],
                              input=json.dumps(payload).encode(), env=mom_env,
                              capture_output=True, timeout=10)
    def network(argv, **kwargs):
        assert argv[-1] == 'family-mom-a-relay'
        payload = json.loads(kwargs['input'])
        assert set(payload) == {'id', 'message', 'time', 'expires'}
        wire_payloads.append(payload)
        result = receiver('dad', 'learner-a', payload)
        result.check_returncode()
        if len(wire_payloads) == 1:
            raise subprocess.TimeoutExpired('simulated lost acknowledgement', 12)
        return result
    with mock.patch.dict(dad['forward_help'].__globals__, {'run': network}):
        rejects(dad['forward_help'], request['id'], 'mom')
        assert not dad['load_help'](request['id']).get('forwarded_to')
        dad['forward_help'](request['id'], 'mom')  # Same ID/expiry, deduplicated retry.
        dad['forward_help'](request['id'], 'mom')  # Local repeated click is a no-op.
    assert len(wire_payloads) == 2
    inbox = list((mom_home / '.local/state/family-lab/requests').glob('*.json'))
    queue = list((mom_home / '.local/state/family-lab/queue').glob('*.json'))
    assert len(inbox) == len(queue) == 1
    received = json.loads(inbox[0].read_text())
    assert received['id'] == request['id'] and received['expires'] == request['expires']
    assert received['person'] == 'learner-a' and received['forwarded_by'] == 'dad'
    assert mom['forward_choices'](received, mom['config']()) == {}
    rejects(mom['forward_help'], received['id'], 'dad')  # No forwarding loops.
    rejects(dad['forward_help'], '../escape', 'mom')
    rejects(dad['forward_help'], request['id'], 'other-helper')
    payload = wire_payloads[0]
    assert receiver('unknown-source', 'learner-a', payload).returncode != 0
    assert receiver('dad', 'other-peer', payload).returncode != 0
    for change in (
        {'person': 'other-peer'}, {'forwarded_by': 'mom'}, {'expires': created + 601},
        {'time': True}, {'time': float('nan')}, {'time': 10**1000}, {'id': '../escape'},
        {'time': created + 120, 'expires': created + 600},
        {'time': created - 700, 'expires': created - 100}, {'message': 'different content'},
    ):
        assert receiver('dad', 'learner-a', dict(payload, **change)).returncode != 0
    assert (mom_home / '.local/state/family-lab/requests').stat().st_mode & 0o077 == 0

    # Notification adapter uses fixed local request ID actions; text never enters argv actions.
    notifications = []
    fresh = dict(request, id='b' * 32)
    dad['enqueue_help'](fresh, 'different-rate-key')
    with mock.patch.dict(dad['notify_help'].__globals__, {'run': lambda argv, **kw: notifications.append(argv)}), \
            mock.patch('shutil.which', side_effect=lambda name: '/fake/' + name):
        dad['notify_help'](fresh, dad['config'](), '/fake/notify', '/fake/terminal')
    action = notifications[-1][notifications[-1].index('--exec') + 1:]
    assert action[-2:] == ['request', fresh['id']]
    assert fresh['message'] not in action
    assert notifications[-1][notifications[-1].index('--exec') - 1].startswith('Message: ')
    with mock.patch.dict(dad['notify_help'].__globals__, {'run': lambda argv, **kw: notifications.append(argv)}), \
            mock.patch('shutil.which', side_effect=lambda name: '/fake/' + name):
        dad['notify_help'](dict(fresh, message='--image=/synthetic/path'), dad['config'](),
                           '/fake/notify', '/fake/terminal')
    assert notifications[-1][notifications[-1].index('--exec') - 1].startswith('Message: --image=')
    notifications = []
    with mock.patch.dict(mom['notify_help'].__globals__, {'run': lambda argv, **kw: notifications.append(argv)}):
        mom['notify_help'](received, mom['config'](), '/fake/notify', '/fake/terminal')
    assert ' (via dad)' in notifications[-1][notifications[-1].index('-u') + 2]
    assert 'request' not in notifications[-1][notifications[-1].index('--exec') + 1:]

    # Zenity choices are mocked: no dialog or notification appears on the host desktop.
    actions = []
    globals_ = dad['request_menu'].__globals__
    def selected_mom(argv, **kwargs):
        assert '--no-markup' in argv and '--extra-button=Ask Mom' in argv
        return subprocess.CompletedProcess(argv, 1, stdout='Ask Mom\n', stderr='')
    with mock.patch.dict(globals_, {'forward_help': lambda *args: actions.append(args),
                                   'run': lambda *args, **kw: None}), \
            mock.patch('shutil.which', side_effect=lambda name: '/fake/' + name), \
            mock.patch('subprocess.run', side_effect=selected_mom):
        dad['request_menu'](fresh['id'])
    assert actions == [(fresh['id'], 'mom')]
    for stdout, returncode, expected in (('', 1, []), ('unexpected', 1, []), ('', 0, ['open'])):
        actions = []
        with mock.patch.dict(globals_, {'forward_help': lambda *args: actions.append('forward'),
                                       'open_help': lambda *args: actions.append('open')}), \
                mock.patch('shutil.which', side_effect=lambda name: '/fake/' + name), \
                mock.patch('subprocess.run', return_value=subprocess.CompletedProcess([], returncode, stdout=stdout)):
            dad['request_menu'](fresh['id'])
        assert actions == expected
    # Expired requests cannot open a menu or extend their lifetime by forwarding.
    path = dad['STATE'] / 'requests' / (fresh['id'] + '.json')
    expired = dict(fresh, time=created - 700, expires=created - 100)
    path.write_text(json.dumps(expired))
    rejects(dad['forward_help'], fresh['id'], 'mom')
    rejects(dad['request_menu'], fresh['id'])
    assert not path.exists()
    # Delivered requests still count against the 20-live-request inbox bound.
    bounded = context(root / 'bounded', {'view_aliases': {'learner-a': 'family-a-view'}})
    for index in range(20):
        bounded['enqueue_help'](dict(request, id=f'{index:032x}'), 'rate-' + str(index))
    rejects(bounded['enqueue_help'], dict(request, id='f' * 32), 'overflow')
    assert len(list((bounded['STATE'] / 'requests').glob('*.json'))) == 20

print('PASS: ask-dad/ask-mom routes, legacy fallback, scoped relay identity, deduplicated lost-ack retry, '
      'expiry, replay/conflict rejection, no loops, literal text, fixed actions and safe menu choices')
