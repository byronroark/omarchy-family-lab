"""Reviewed menu plans; privilege stays in fixed operations, never in menu strings."""
import hashlib,json,os,pathlib,pwd,re,subprocess
CATALOG=pathlib.Path(__file__).with_name('family-menu-catalog.json')
def catalog():return json.loads(CATALOG.read_text())
def entry(identifier):
    if not isinstance(identifier,str) or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,127}',identifier):raise ValueError('Invalid menu ID')
    value=catalog().get(identifier)
    if not value:raise ValueError('This menu action needs enrollment/review')
    return value
def check_sources(value):
    hashes=dict(value.get('hashes',{}))
    if 'script' in value:hashes[value['script']]=value['sha256']
    if value.get('gpu'):hashes['omarchy-install-gaming-gpu-lib32']=catalog()['_gpu_source']['sha256']
    for name,digest in hashes.items():
        path=pathlib.Path('/usr/bin')/name
        st=path.lstat()
        if path.is_symlink() or st.st_uid!=0 or st.st_mode&0o022 or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Installer changed; review required: '+name)
def gpu_packages():
    names=[]
    devices=subprocess.check_output(['/usr/bin/lspci'],text=True)
    for vendor,package in [('Intel','lib32-vulkan-intel'),('AMD','lib32-vulkan-radeon')]:
        if any(re.search(r'(VGA|Display).*'+vendor,line,re.I) for line in devices.splitlines()):names.append(package)
    for helper,package in [('omarchy-hw-nvidia-gsp','lib32-nvidia-utils'),('omarchy-hw-nvidia-without-gsp','lib32-nvidia-580xx-utils')]:
        if subprocess.run(['/usr/bin/'+helper],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:names.append(package);break
    return names
def package_command(packages):
    if any(not re.fullmatch(r'[a-z0-9@_+][a-z0-9@._+-]*',x) for x in packages):raise ValueError('Invalid catalog package')
    return ['/usr/bin/pacman','-S','--needed','--',*packages]
def plan(identifier):
    value=entry(identifier);check_sources(value)
    names=(gpu_packages() if value.get('gpu') else [])+value['packages']
    return value,list(dict.fromkeys(names))
def child_command(child,identifier):
    return ['/usr/bin/setpriv','--reuid='+str(child.pw_uid),'--regid='+str(child.pw_gid),'--init-groups','--no-new-privs',
      '/usr/bin/env','-i','HOME='+child.pw_dir,'USER='+child.pw_name,'LOGNAME='+child.pw_name,'PATH=/usr/local/libexec/family-software-shims:/usr/bin:/bin',
      'OMARCHY_PATH=/usr/share/omarchy','LANG=C.UTF-8','TERM=xterm-256color','XDG_RUNTIME_DIR=/run/user/'+str(child.pw_uid),
      'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/'+str(child.pw_uid)+'/bus','/usr/local/libexec/family-menu-action','--user',identifier]
def user_step(identifier):
    cfg=json.loads(pathlib.Path('/etc/family-help/child.json').read_text())
    if os.getuid()!=cfg['uid'] or os.geteuid()==0:raise ValueError('User settings must run as the enrolled learner')
    value=entry(identifier);check_sources(value)
    # These are only child-session values; they never enter a root command environment.
    result=subprocess.run(['/usr/bin/systemctl','--user','show-environment'],capture_output=True,text=True)
    for line in result.stdout.splitlines():
        key,sep,data=line.partition('=')
        if sep and key in ('WAYLAND_DISPLAY','DISPLAY','HYPRLAND_INSTANCE_SIGNATURE','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE'):os.environ[key]=data
    if value['mode']=='agent':
        agent=value['agent']
        if agent in ('hermes','openclaw'):
            subprocess.run(['/usr/bin/omarchy-install-'+('hermes' if agent=='hermes' else 'openclaw')+'-cli','--now'],check=True,stdin=subprocess.DEVNULL)
        else:
            package={'omp':'github:can1357/oh-my-pi','grok':'npm:@xai-official/grok','muse':'http:muse[url=https://api.meta.ai/muse-launcher.sh,bin=muse,version_list_url=https://api.meta.ai/muse-code/channels/muse-stable,version_json_path=.version]'}.get(agent,agent)
            subprocess.run(['/usr/bin/mise','use','-g',package],check=True,stdin=subprocess.DEVNULL)
        path=pathlib.Path.home()/'.config/omarchy/defaults/agent';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(agent+'\n')
        print('Default agent set for the learner. Open the agent on the learner desktop to sign in.');return
    if value['mode']=='script':
        body=(pathlib.Path('/usr/bin')/value['script']).read_text()
        if value.get('extra')=='lutris-python':body=body.replace("sudo sed -i '/env python3/ c\\#!/bin/python3' /usr/bin/lutris",': # Parent already applied the reviewed system shebang repair')
        subprocess.run(['/usr/bin/bash','-e','-c',body,'family-menu-user',*value.get('args',[])],check=True,stdin=subprocess.DEVNULL)
    elif value.get('desktop'):
        subprocess.Popen(['/usr/bin/gtk-launch',value['desktop']],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
def run(identifier,cfg,env):
    value,packages=plan(identifier)
    if value['mode']=='manual':
        print('Manual parent review required. No menu command was executed.\nAction: '+identifier+'\nOriginal menu entry (reference only): '+value['original'])
        return 'manual-review',0
    if packages:subprocess.run(package_command(packages),env=env,cwd='/root',check=True)
    child=pwd.getpwnam(cfg['child'])
    if value['mode']=='controllers':
        # Fixed enrolled identity and fixed system destinations; no child-supplied paths.
        for path,text in [('/etc/modprobe.d/blacklist-xpad.conf','blacklist xpad\n'),('/etc/modules-load.d/xpadneo.conf','hid_xpadneo\n')]:
            target=pathlib.Path(path)
            if target.is_symlink() or target.parent.is_symlink() or target.parent.stat().st_uid!=0 or target.parent.stat().st_mode&0o022:raise ValueError('Unsafe driver configuration path')
            if target.exists() and (target.stat().st_uid!=0 or target.stat().st_mode&0o022):raise ValueError('Unsafe existing driver configuration')
            target.write_text(text);target.chmod(0o644)
        subprocess.run(['/usr/bin/usermod','-aG','input',child.pw_name],env=env,check=True)
        print('Controller driver configured. Save work and arrange a reboot separately; none is performed now.')
    elif value.get('extra')=='lutris-python':
        target=pathlib.Path('/usr/bin/lutris');st=target.lstat()
        if target.is_symlink() or st.st_uid!=0 or st.st_mode&0o022:raise ValueError('Unsafe Lutris executable')
        subprocess.run(['/usr/bin/sed','-i','/env python3/ c\\#!/bin/python3',str(target)],env=env,check=True)
    if value['mode'] in ('script','agent','package'):
        subprocess.run(child_command(child,identifier),env=env,cwd=child.pw_dir,stdin=subprocess.DEVNULL,close_fds=True,check=True)
    return 'completed',0
