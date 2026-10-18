import fcntl,json,os,pathlib,pty,select,signal,subprocess,tempfile,termios,time
source=(pathlib.Path(__file__).resolve().parents[1]/'assistance/family-help-child').read_text()
with tempfile.TemporaryDirectory(prefix='family-help-test-',dir='/tmp') as temp:
    base=pathlib.Path(temp);sock=str(base/'tmux.sock');state=base/'state';conf=base/'child.json';script=base/'child'
    (base/'family_identity.py').write_bytes((pathlib.Path(__file__).resolve().parents[1]/'assistance/family_identity.py').read_bytes())
    conf.write_text(json.dumps({'uid':os.getuid(),'state':str(state),'socket':sock,'session':'learning','viewer':'unused'}))
    script.write_text(source.replace('/etc/family-help/child.json',str(conf)));script.chmod(0o700)
    tmux=['/usr/bin/tmux','-S',sock,'-f','/dev/null']
    subprocess.run(tmux+['new-session','-d','-s','learning','/usr/bin/bash','--noprofile','--norc'],check=True)
    def call(mode):return subprocess.run(['/usr/bin/python3',str(script),mode],check=True,capture_output=True,text=True,timeout=5)
    def waitfor(condition,seconds=5):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if condition():return
            time.sleep(.05)
        raise AssertionError('Condition timed out')
    def start():
        master,slave=pty.openpty()
        def setup():os.setsid();fcntl.ioctl(slave,termios.TIOCSCTTY,0)
        proc=subprocess.Popen(['/usr/bin/python3',str(script),'help'],stdin=slave,stdout=slave,stderr=slave,
                              preexec_fn=setup,env=dict(os.environ,TERM='xterm-256color'))
        os.close(slave);waitfor(lambda:(state/'control-request.json').exists());return proc,master
    try:
        proc,master=start()
        assert not (state/'consent.json').exists() and proc.poll() is None
        call('allow');original=json.loads((state/'consent.json').read_text());call('allow')
        assert json.loads((state/'consent.json').read_text())==original,'Duplicate approval changed grant'
        time.sleep(.4);assert proc.poll() is None,'Client exited after approval'
        marker=base/'typed'
        os.write(master,('printf ok > '+str(marker)+'\r').encode());waitfor(marker.exists)
        assert marker.read_text()=='ok'
        call('revoke');proc.wait(timeout=3);os.close(master)
        assert subprocess.run(tmux+['has-session','-t','=learning']).returncode==0
        print('PASS: waits for consent, duplicate allow idempotent, real typing, revoke disconnects, learning survives')
        proc,master=start();call('allow');time.sleep(.4)
        grant=json.loads((state/'consent.json').read_text());grant['expires']=time.time()+.5
        (state/'consent.json').write_text(json.dumps(grant));proc.wait(timeout=3);os.close(master)
        print('PASS: expired/shortened permission disconnects')
        proc,master=start();call('allow');time.sleep(.4);proc.terminate();proc.wait(timeout=3);os.close(master)
        time.sleep(.2)
        clients=subprocess.run(tmux+['list-clients','-F','#{client_pid}'],capture_output=True,text=True)
        assert not clients.stdout.strip(),'Typing client survived supervisor exit'
        assert not (state/'consent.json').exists()
        print('PASS: supervisor exit disconnects client and clears permission')
    finally:
        subprocess.run(tmux+['kill-server'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
