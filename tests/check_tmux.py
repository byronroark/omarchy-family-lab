import os, pathlib, subprocess, tempfile, pty, fcntl, termios, time
script=str((pathlib.Path(__file__).resolve().parents[1] / 'scripts/family-lab'))
with tempfile.TemporaryDirectory() as d:
    env=dict(os.environ, TMUX_TMPDIR=d, TERM='xterm-256color')
    base=['tmux','-L','family-lab','-f','/dev/null']
    subprocess.run(base+['new-session','-d','-s','learning'],env=env,check=True)
    master,slave=pty.openpty()
    def setup():
        os.setsid()
        fcntl.ioctl(slave,termios.TIOCSCTTY,0)
    proc=None
    try:
        proc=subprocess.Popen(['python3',script,'view'],env=env,stdin=slave,stdout=slave,stderr=slave,preexec_fn=setup)
        time.sleep(0.4)
        result=subprocess.run(base+['list-clients','-F','#{client_flags}'],env=env,check=True,capture_output=True,text=True)
        assert 'read-only' in result.stdout, result.stdout
        subprocess.run(base+['kill-server'],env=env,check=True)
        proc.wait(timeout=3)
        print('PASS: real isolated tmux viewer is read-only and stop disconnects it')
    finally:
        if proc and proc.poll() is None: proc.terminate()
        subprocess.run(base+['kill-server'],env=env,capture_output=True)
        os.close(master); os.close(slave)
