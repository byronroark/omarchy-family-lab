#!/usr/bin/env python3
"""Hermetic report validation and separate SSH/LocalSend boundaries."""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('reporting', str(Path(__file__).resolve().parents[1] / 'scripts/family-lab-report'))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)
with tempfile.TemporaryDirectory() as directory:
    m.ROOT = Path(directory) / 'state'
    m.CONFIG = Path(directory) / 'config.json'
    m.CONFIG.write_text(json.dumps({'reporting': {'enabled': False}}))
    try:
        m.render('2026-01-01', '2026-01-01')
        raise AssertionError('disabled reporting accepted')
    except ValueError:
        pass
    m.CONFIG.write_text(json.dumps({'reporting': {'enabled': True}}))
    assert 'Unknown' in m.render('2026-01-01', '2026-01-01')
    data = {'schema': 1, 'coverage': 'Synthetic test observations', 'observations': [
        {'start': '2026-01-01T23:50:00+00:00', 'end': '2026-01-02T00:10:00+00:00',
         'app': '<script>|[click](bad)', 'domain': 'example.org', 'category': 'Learning'}]}
    source = Path(directory) / 'sample.json'
    source.write_text(json.dumps(data))
    m.main(['import', str(source)])
    report = m.render('2026-01-01', '2026-01-01')
    assert '**10.0 minutes**' in report and '<script>' not in report and '[click]' not in report
    assert 'example.org' in report and 'UTC' in report
    data['observations'][0]['domain'] = 'https://example.org/private?q=secret'
    try:
        m.validate(data)
        raise AssertionError('full URL accepted')
    except ValueError:
        pass
    data['observations'][0]['domain'] = None
    data['observations'] *= 2
    try:
        m.validate(data)
        raise AssertionError('overlap accepted')
    except ValueError:
        pass
    try:
        m.main(['request', 'learner-a', '2026-01-01', '2026-01-01'])
        raise AssertionError('unenrolled report key accepted')
    except ValueError:
        pass
    try:
        m.main(['serve', 'dad'])
        raise AssertionError('unenrolled helper accepted')
    except ValueError:
        pass
    # Exercise the actual forced-command process with isolated HOME and stdin.
    home = Path(directory) / 'home'
    conf = home / '.config/family-lab/config.json'
    conf.parent.mkdir(parents=True)
    conf.write_text(json.dumps({'reporting': {'enabled': True, 'allowed_helpers': ['dad']}}))
    script = str(Path(__file__).resolve().parents[1] / 'scripts/family-lab-report')
    env = dict(os.environ, HOME=str(home), SSH_ORIGINAL_COMMAND='arbitrary ignored command')
    response = subprocess.run([sys.executable, script, 'serve', 'dad'], input=b'{"start":"2026-01-01","end":"2026-01-01"}', capture_output=True, env=env, timeout=8)
    assert response.returncode == 0 and response.stdout.startswith(b'# Family Lab activity report')
    for payload in (b'x'*513, b'{"start":"bad","end":"bad"}', b'{"start":"2026-01-01","end":"2026-01-01","command":"ignored"}'):
        response = subprocess.run([sys.executable, script, 'serve', 'dad'], input=payload, capture_output=True, env=env, timeout=8)
        assert response.returncode != 0 and not response.stdout
    saved = m.save(report)
    assert saved.stat().st_mode & 0o077 == 0
    with patch.object(m.shutil, 'which', return_value='/test/localsend-cli'), patch.object(m.subprocess, 'run') as run:
        m.main(['share', str(saved)])
        assert run.call_args.args[0] == ['/test/localsend-cli', 'send', str(saved)]
    try:
        m.main(['share', str(source)])
        raise AssertionError('arbitrary file sharing accepted')
    except ValueError:
        pass
print('Reporting checks passed (no real network, household data, or desktop changes).')
