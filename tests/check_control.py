"""Real Linux PTY/tmux consent lifecycle checks on an isolated home and socket."""
import json
import os
import pathlib
import pty
import fcntl
import select
import shlex
import subprocess
import tempfile
import termios
import threading
import time

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts/family-lab'


def wait_for(predicate, description, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError('Timed out: ' + description)


with tempfile.TemporaryDirectory() as directory:
    env = dict(os.environ, HOME=directory, TMUX_TMPDIR=directory, TERM='xterm-256color', SHELL='/bin/sh')
    for name in ('TMUX', 'SSH_CONNECTION', 'SSH_TTY'):
        env.pop(name, None)
    remote_env = dict(env, SSH_CONNECTION='synthetic SSH context')
    base = ['tmux', '-L', 'family-lab', '-f', '/dev/null']
    state = pathlib.Path(directory) / '.local/state/family-lab/control.json'
    processes = []
    fds = []
    outputs = {}
    readers = []
    done = threading.Event()

    def tmux(*args):
        return subprocess.run(base + list(args), env=env, check=True, capture_output=True, text=True).stdout

    def terminal(*args, remote=False):
        master, slave = pty.openpty()
        fds.extend((master, slave))
        def setup():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
        proc = subprocess.Popen(['python3', str(SCRIPT), *args], env=remote_env if remote else env,
                                stdin=slave, stdout=slave, stderr=slave, preexec_fn=setup)
        processes.append(proc)
        outputs[master] = bytearray()
        def drain():
            while not done.is_set():
                try:
                    if select.select([master], [], [], 0.1)[0]:
                        data = os.read(master, 65536)
                        if not data:
                            return
                        outputs[master].extend(data)
                        del outputs[master][:-65536]
                except OSError:
                    return
        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        readers.append(reader)
        return proc, master

    def record():
        try:
            return json.loads(state.read_text())
        except FileNotFoundError:
            return {}

    def readonly(pid):
        return any(line.split('\t') == [str(pid), '1'] for line in
                   tmux('list-clients', '-F', '#{client_pid}\t#{client_readonly}').splitlines())

    def request(helper=None):
        proc, fd = terminal('control', *([helper] if helper else []), remote=True)
        try:
            wait_for(lambda: record().get('phase') == 'pending', 'pending connection')
        except AssertionError:
            print('Control process:', proc.poll(), 'output:', bytes(outputs[fd]))
            raise
        return proc, fd, record()['pid']

    def approve(seconds='300', answer=b'yes\n'):
        proc, fd = terminal('allow-control', seconds)
        os.write(fd, answer)
        proc.wait(timeout=5)
        assert proc.returncode == 0

    def cli(*args):
        return subprocess.run(['python3', str(SCRIPT), *args], env=env, capture_output=True, timeout=5)

    try:
        learner, learner_fd = terminal('learn')
        wait_for(lambda: subprocess.run(base + ['has-session', '-t', '=learning'], env=env,
                                       capture_output=True).returncode == 0, 'learning session')
        wait_for(lambda: 'C-r' in tmux('list-keys', '-T', 'prefix'), 'revoke shortcut')
        original_clients = set(tmux('list-clients', '-F', '#{client_name}').splitlines())
        reattached, reattached_fd = terminal('learn')
        wait_for(lambda: len(tmux('list-clients', '-F', '#{client_pid}').splitlines()) == 2,
                 'learn reattaches to an existing session')
        # Being listed by the server does not mean the new client's terminal
        # input is ready. Detach that exact client via the server instead of
        # racing its startup with a Ctrl+b,d byte sequence on a loaded runner.
        names = set(tmux('list-clients', '-F', '#{client_name}').splitlines()) - original_clients
        assert len(names) == 1
        tmux('detach-client', '-t', names.pop())
        reattached.wait(timeout=5)
        assert reattached.returncode == 0
        assert learner.poll() is None
        assert set(tmux('list-clients', '-F', '#{client_name}').splitlines()) == original_clients
        assert cli('allow-control').returncode != 0  # No piped/unattended approvals.
        assert cli('assist', 'learner-a').returncode != 0  # Not enabled by default.
        viewer, viewer_fd = terminal('view', remote=True)
        wait_for(lambda: readonly(viewer.pid), 'independent read-only viewer')
        helper, helper_fd, pid = request()
        assert readonly(pid)
        # Read-only input must not execute a shell command.
        blocked = pathlib.Path(directory) / 'blocked'
        os.write(helper_fd, ('touch ' + shlex.quote(str(blocked)) + '\n').encode())
        time.sleep(0.15)
        assert not blocked.exists()
        duplicate, _ = terminal('control', remote=True)
        duplicate.wait(timeout=5)
        assert duplicate.returncode != 0
        assert readonly(pid)
        rejected, rejected_fd = terminal('allow-control', remote=True)
        os.write(rejected_fd, b'yes\n')
        rejected.wait(timeout=5)
        assert rejected.returncode != 0  # Ordinary SSH approval is rejected.
        approve(answer=b'no\n')
        helper.wait(timeout=5)
        assert not state.exists()

        # A delayed yes for a disconnected request must not approve a reconnect.
        helper, helper_fd, pid = request()
        old_approval, old_approval_fd = terminal('allow-control')
        wait_for(lambda: b'Type yes:' in outputs[old_approval_fd], 'local approval prompt')
        assert cli('revoke-control').returncode == 0
        helper.wait(timeout=5)
        helper, helper_fd, pid = request()
        os.write(old_approval_fd, b'yes\n')
        old_approval.wait(timeout=5)
        assert old_approval.returncode != 0
        assert record()['phase'] == 'pending' and readonly(pid)
        # Simulate the monotonic pending deadline to test rejection without a minute-long wait.
        expired = record()
        expired['deadline'] = time.clock_gettime(time.CLOCK_BOOTTIME) - 1
        temp = state.with_suffix('.test-tmp')
        temp.write_text(json.dumps(expired))
        temp.replace(state)
        helper.wait(timeout=5)
        assert not state.exists()

        helper, helper_fd, pid = request()
        approve()
        wait_for(lambda: record().get('phase') == 'active', 'approved writable client')
        assert not readonly(pid)
        assert readonly(viewer.pid)  # Approval must never promote ordinary viewers.
        assert 'HELPER CAN TYPE' in tmux('show-options', '-v', '-t', 'learning', 'status-right')
        marker = pathlib.Path(directory) / 'helper-command-ran'
        os.write(helper_fd, ('touch ' + shlex.quote(str(marker)) + '\n').encode())
        wait_for(marker.exists, 'approved helper command executes')
        # Revoke via the learner client shortcut, even while a foreground job runs.
        os.write(learner_fd, b'sleep 10\n')
        time.sleep(0.1)
        os.write(learner_fd, b'\x02\x12')  # Ctrl+b, Ctrl+r.
        helper.wait(timeout=5)
        assert not state.exists()
        assert 'HELP VIEW ONLY' in tmux('show-options', '-v', '-t', 'learning', 'status-right')
        os.write(learner_fd, b'\x03')  # End the test foreground job; revoke itself did not kill it.

        # Every reconnect is read-only again; short approval expires and disconnects.
        helper, helper_fd, pid = request()
        assert readonly(pid)
        approve('1')
        wait_for(lambda: record().get('phase') == 'active', 'short control approval')
        helper.wait(timeout=5)
        assert not state.exists()

        # Abrupt supervisor death must not leave its tmux client writable.
        helper, helper_fd, pid = request()
        approve()
        wait_for(lambda: record().get('phase') == 'active', 'approval before supervisor failure')
        helper.kill()
        helper.wait(timeout=5)
        wait_for(lambda: str(pid) not in tmux('list-clients', '-F', '#{client_pid}').splitlines(),
                 'child detached after supervisor death')
        assert cli('revoke-control').returncode == 0

        # Named helper comes from the forced key argument, not the approval or message.
        helper, helper_fd, pid = request('mom')
        assert record()['helper'] == 'mom'
        approve()
        wait_for(lambda: record().get('phase') == 'active', 'approval before stop')
        assert 'MOM CAN TYPE' in tmux('show-options', '-v', '-t', 'learning', 'status-right')
        # Stop also disconnects the control client and clears its request.
        assert cli('stop').returncode == 0
        helper.wait(timeout=5)
        assert not state.exists()
    finally:
        subprocess.run(base + ['kill-server'], env=env, capture_output=True)
        for proc in processes:
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)
        done.set()
        for reader in readers:
            reader.join(timeout=1)
        for fd in fds:
            os.close(fd)
    print('PASS: pending read-only input, local confirmation, decline, stale approval, pending expiry, '
          'independent viewer remains read-only, single connection, writable command, '
          'visible status, shortcut revoke during foreground job, fresh approval, expiry, supervisor failure and stop')
