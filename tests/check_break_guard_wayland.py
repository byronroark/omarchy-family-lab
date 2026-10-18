"""Lock only a disposable nested compositor. Never targets the live desktop."""
import json,os,pathlib,shutil,socket,stat,subprocess,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
parent=pathlib.Path(os.environ['XDG_RUNTIME_DIR'])/os.environ['WAYLAND_DISPLAY']
if pathlib.Path(os.environ['WAYLAND_DISPLAY']).is_absolute():parent=pathlib.Path(os.environ['WAYLAND_DISPLAY'])
with tempfile.TemporaryDirectory(prefix='family-nested-guard-') as directory:
    temp=pathlib.Path(directory);runtime=temp/'runtime';runtime.mkdir(mode=0o700);home=temp/'home';home.mkdir()
    config=temp/'hyprland.lua';config.write_text('hl.config({misc={disable_hyprland_logo=true,disable_splash_rendering=true,allow_session_lock_restore=true},animations={enabled=false}})\nhl.monitor({output="",mode="800x740",position="auto",scale=1})\n')
    env=dict(os.environ,HOME=str(home),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(home/'.config'),XDG_CACHE_HOME=str(home/'.cache'),WAYLAND_DISPLAY=str(parent),AQ_NO_KMS_REQUIREMENT='1')
    env.pop('WAYLAND_SOCKET',None);env.pop('HYPRLAND_INSTANCE_SIGNATURE',None)
    log=(temp/'compositor.log').open('w+')
    compositor=subprocess.Popen(['/usr/bin/Hyprland','--config',str(config)],env=env,stdout=log,stderr=subprocess.STDOUT)
    ui=None
    try:
        server=None;deadline=time.monotonic()+10
        while server is None and compositor.poll() is None and time.monotonic()<deadline:
            found=[p for p in runtime.glob('wayland-*') if stat.S_ISSOCK(p.lstat().st_mode)]
            if found:server=found[0]
            else:time.sleep(.1)
        if server is None:
            log.seek(0);raise AssertionError('Nested compositor failed: '+log.read()[-2500:])
        assert server.parent==runtime and str(server)!=str(parent)
        state={'healthy':True,'blocked':True,'phase':'due','remaining_seconds':900,'helpers':['dad','mom'],'episode':'a'*32,'revision':0,'reason':'break'}
        fixture=temp/'state.json';fixture.write_text(json.dumps(state));ack=temp/'protected'
        stub=temp/'policy-stub'
        stub.write_text('#!/usr/bin/python3\nimport sys,json,pathlib\np=pathlib.Path('+repr(str(fixture))+'); state=json.loads(p.read_text())\nif sys.argv[1:]==["guard","get"]:print(json.dumps(state))\nelif sys.argv[1:3]==["guard","protected"]:\n state["phase"]="break"; p.write_text(json.dumps(state)); pathlib.Path('+repr(str(ack))+').write_text("secure"); print("{}")\nelif sys.argv[1:]==["guard","release"]:print(json.dumps({"allowed":state["healthy"] and not state["blocked"]}))\nelse:sys.exit(1)\n');stub.chmod(0o700)
        copied=temp/'Dino';shutil.copytree(ROOT/'guardian',copied)
        (copied/'guard/Dino').mkdir()
        for name in ('BreakCard.qml','PixelDino.qml'):shutil.copy2(ROOT/'guardian'/name,copied/'guard/Dino'/name)
        qml=copied/'guard/shell.qml';source=qml.read_text().replace('/usr/local/libexec/family-lab-policy',str(stub))
        source=source.replace('onSecureChanged: root.protect()', 'onSecureChanged: { console.log("TEST_GUARD_SECURE=" + secure); root.protect() }')
        source=source.replace('    Component.onCompleted: root.refresh()', '    Timer { interval: 200; running: true; repeat: true; onTriggered: { if (root.state.healthy && !root.state.blocked && !release.running) release.running = true } }\n    Component.onCompleted: root.refresh()')
        qml.write_text(source)
        ui_log=(temp/'ui.log').open('w+')
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
            connection.connect(str(server));ui_env=dict(env,WAYLAND_SOCKET=str(connection.fileno()),QT_QPA_PLATFORM='wayland',QT_QPA_PLATFORMTHEME='basic',QT_QUICK_CONTROLS_STYLE='Basic',QT_QUICK_BACKEND='software')
            ui_env.pop('WAYLAND_DISPLAY',None)
            ui=subprocess.Popen(['/usr/bin/quickshell','--no-color','-p',str(copied/'guard')],env=ui_env,stdout=ui_log,stderr=subprocess.STDOUT,pass_fds=(connection.fileno(),))
        deadline=time.monotonic()+10
        while not ack.exists() and ui.poll() is None and time.monotonic()<deadline:time.sleep(.1)
        ui_log.flush();ui_log.seek(0);output=ui_log.read()
        assert ack.exists() and ui.poll() is None,output[-3000:]
        # Kill only the locker in this disposable compositor. Its replacement
        # must recover the orphaned lock without creating a new break episode.
        ui.kill();ui.wait(timeout=3);ui_log.seek(0,2)
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
            connection.connect(str(server));ui_env['WAYLAND_SOCKET']=str(connection.fileno())
            ui=subprocess.Popen(['/usr/bin/quickshell','--no-color','-p',str(copied/'guard')],env=ui_env,stdout=ui_log,stderr=subprocess.STDOUT,pass_fds=(connection.fileno(),))
        deadline=time.monotonic()+8;recovered=False
        while ui.poll() is None and time.monotonic()<deadline:
            ui_log.flush();ui_log.seek(0);output=ui_log.read()
            if output.count('TEST_GUARD_SECURE=true')>=2:recovered=True;break
            time.sleep(.1)
        assert recovered,output[-3000:]
        state=json.loads(fixture.read_text());assert state['episode']=='a'*32 and state['phase']=='break'
        state['healthy']=False;fixture.write_text(json.dumps(state));time.sleep(1.5)
        assert ui.poll() is None,'Guard exited on stale policy'
        state.update(healthy=True,blocked=False,phase='use',episode=None,remaining_seconds=0);fixture.write_text(json.dumps(state))
        ui.wait(timeout=6);ui_log.flush();ui_log.seek(0);output=ui_log.read()
        assert ui.returncode==0 and 'TEST_GUARD_SECURE=true' in output,output[-3000:]
        assert not any(word in output for word in ('ReferenceError','TypeError','Unable to assign','Cannot assign')),output[-3000:]
        print('PASS: actual nested Wayland lock secured, recovered after locker death without resetting the episode, stayed locked on unhealthy status, and released only after fresh permission. Main desktop was never targeted.')
    finally:
        for process in (ui,compositor):
            if process and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
        log.close()
