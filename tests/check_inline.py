"""Inline backend contract, DND, action validation and native fallback; no desktop calls."""
import contextlib
import io
import json
import os
import pathlib
import runpy
import subprocess
import tempfile
import time
from unittest import mock

script = pathlib.Path(__file__).resolve().parents[1] / 'scripts/family-lab'
with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
    home = pathlib.Path(directory)
    config_path = home / '.config/family-lab/config.json'
    config_path.parent.mkdir(parents=True)
    cfg = {'notification_backend': 'inline', 'view_aliases': {'learner-a': 'learner-view'},
           'forward_routes': {'mom': {'learner-a': 'mom-relay'}}}
    config_path.write_text(json.dumps(cfg))
    with mock.patch.dict(os.environ, {'HOME': directory}):
        ctx = runpy.run_path(str(script), run_name='test_family_inline')
    globals_ = ctx['ui_state'].__globals__
    created = time.time()
    request = {'id': 'a' * 32, 'person': 'learner-a', 'message': '<b>literal</b> $(not-a-command)',
               'time': created, 'expires': created + 600}
    ctx['enqueue_help'](request, 'learner-a')
    queue = ctx['STATE'] / 'queue' / (request['id'] + '.json')
    saved = ctx['STATE'] / 'requests' / queue.name
    def dnd(off=True):
        return subprocess.CompletedProcess([], 0, stdout='off\n' if off else 'on\n')
    with mock.patch.dict(globals_, {'run': lambda *args, **kw: dnd()}):
        state = ctx['ui_state']()
    assert state['version'] == 1 and state['enabled'] and not state['paused']
    assert ctx['pending_native'](cfg)  # Reading data alone does not certify a working renderer.
    ctx['ui_heartbeat']()  # Simulate the plugin confirming successful load/render readiness.
    row = state['requests'][0]
    assert row['message'] == request['message']
    assert ctx['peer_label']('learner-a', {'peer_labels': {'learner-a': 'Alex Rivera'}}) == 'Alex Rivera (learner-a)'
    assert ctx['peer_label']('alex', {}) == 'alex'
    try:
        ctx['peer_label']('alex', {'peer_labels': {'alex': 'bad\nname'}})
        raise AssertionError('Control character accepted in label')
    except ValueError:
        pass
    assert row['actions'] == [{'kind': 'open', 'label': 'Open terminal'},
                             {'kind': 'forward', 'label': 'Ask Mom', 'target': 'mom'},
                             {'kind': 'dismiss', 'label': 'Dismiss'}]
    assert not ctx['pending_native'](cfg)
    queue.unlink()  # Simulate watcher handing delivery to the healthy plugin.
    with ctx['request_lock']():
        ctx['restore_native_queue'](cfg)
    assert not queue.exists()
    heartbeat = ctx['STATE'] / 'inline-heartbeat.json'
    heartbeat.write_text(json.dumps({'time': time.time() - 20}))
    assert ctx['pending_native'](cfg)
    with ctx['request_lock']():
        ctx['restore_native_queue'](cfg)
    assert queue.exists()  # Plugin failure recovers the still-unhandled request.
    with mock.patch.dict(globals_, {'run': lambda *args, **kw: dnd(False)}):
        paused = ctx['ui_state']()
    assert paused['paused'] and paused['requests'] == []
    heartbeat.write_text(json.dumps({'time': time.time() - 20}))
    def fail(*args, **kw):
        raise subprocess.TimeoutExpired('synthetic failure', 3)
    try:
        with mock.patch.dict(globals_, {'run': fail}):
            ctx['ui_state']()
    except subprocess.TimeoutExpired:
        pass
    else:
        raise AssertionError('Unknown DND state must fail closed')
    assert ctx['pending_native'](cfg)  # Failed probe did not renew heartbeat.
    for action in ('allow-control', 'control', 'sudo', 'arbitrary'):
        try:
            ctx['ui_action']([request['id'], action])
        except ValueError:
            pass
        else:
            raise AssertionError('UI must not support control approval or arbitrary execution')
    assert not json.loads(saved.read_text()).get('ui_dismissed')
    with mock.patch.dict(globals_, {'open_help': fail}), mock.patch('shutil.which', return_value='/fake/terminal'):
        try:
            ctx['ui_action']([request['id'], 'open'])
        except subprocess.TimeoutExpired:
            pass
        else:
            raise AssertionError('Failed action must remain retryable')
    assert not json.loads(saved.read_text()).get('ui_dismissed')
    actions = []
    with mock.patch.dict(globals_, {'forward_help': lambda *args: actions.append(args)}):
        ctx['ui_action']([request['id'], 'forward', 'mom'])
    assert actions == [(request['id'], 'mom')]
    assert json.loads(saved.read_text())['ui_dismissed']
    queue.unlink()
    with ctx['request_lock']():
        ctx['restore_native_queue']({'notification_backend': 'native'})
    assert not queue.exists()  # Dismissal never reappears through fallback.
    # Native-delivered cards do not duplicate into the inline surface.
    data = dict(request, id='b' * 32)
    ctx['enqueue_help'](data, 'different-rate')
    native = ctx['STATE'] / 'requests' / (data['id'] + '.json')
    native_data = json.loads(native.read_text()); native_data['native_notified'] = True
    native.write_text(json.dumps(native_data))
    with mock.patch.dict(globals_, {'run': lambda *args, **kw: dnd()}):
        assert ctx['ui_state']()['requests'] == []
    cfg['notification_backend'] = 'native'
    config_path.write_text(json.dumps(cfg))
    with mock.patch.dict(globals_, {'run': fail}):
        assert ctx['ui_state']() == {'version': 1, 'enabled': False, 'paused': False, 'requests': []}
print('PASS: inline actions, DND/unknown-DND, heartbeat failure recovery, native deduplication, '
      'dismissal, failed-action retry and no control/admin actions')
