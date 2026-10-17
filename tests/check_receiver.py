import json, os, pathlib, subprocess, tempfile
script = (pathlib.Path(__file__).resolve().parents[1] / 'scripts/family-lab')
with tempfile.TemporaryDirectory() as d:
    env = dict(os.environ, HOME=d)
    def call(*args, payload=None):
        return subprocess.run(['python3', str(script), *args], input=payload,
                              capture_output=True, env=env, timeout=10)
    # The execution host can run as an unprivileged user; never mutate real HOME.
    installed = call('install')
    if os.geteuid() != 0:
        assert installed.returncode == 0, installed.stderr
        assert (pathlib.Path(d)/'.local/bin/ask-dad').is_symlink()
        assert call('install').returncode != 0
    config_path = pathlib.Path(d)/'.config/family-lab/config.json'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({'view_aliases': {'learner-a': 'family-learner-a-view', 'learner-b': 'family-learner-b-view'}}))
    for who in ('learner-a', 'learner-b'):
        result = call('receive', who, payload=json.dumps({'message':'Please explain $(touch NEVER) <b>hi</b>'}).encode())
        assert result.returncode == 0, result.stderr
        assert call('receive', who, payload=b'{"message":"again"}').returncode != 0
    queue = pathlib.Path(d)/'.local/state/family-lab/queue'
    items = [json.loads(p.read_text()) for p in queue.glob('*.json')]
    assert {x['person'] for x in items} == {'learner-a', 'learner-b'}
    assert not pathlib.Path('NEVER').exists()
    assert call('receive','unknown',payload=b'{"message":"hi"}').returncode != 0
    for payload in (b'not json', b'[]', b'null', b'{"message":123}', b'{"message":"hi","command":"id"}', b'{"message":"line\\nline"}', json.dumps({'message':'x'*301}).encode(), b'x'*2049):
        assert call('receive','learner-a',payload=payload).returncode != 0
    assert len(list(queue.glob('*.json'))) == 2
    assert queue.stat().st_mode & 0o077 == 0
print('PASS: isolated installation checks, identity, cooldown, literal message, malformed/oversize rejection and private queue')
