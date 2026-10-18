"""Executed only as the intended desktop user. Never invokes sudo."""
import json,os,pathlib,re,subprocess,sys
os.umask(0o077)
def write(path,data,mode=0o600):
    if path.is_symlink():raise ValueError('Refuse symlink-managed user file: '+str(path))
    data=data.encode() if isinstance(data,str) else data
    if path.exists() and path.read_bytes()==data and path.stat().st_mode&0o777==mode:return False
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if path.exists():
        backup=path.with_name(path.name+'.before-family-setup')
        if not backup.exists():backup.write_bytes(path.read_bytes())
    temp=path.with_name(path.name+'.family.tmp');temp.write_bytes(data);temp.chmod(mode);temp.replace(path);return True

def main(payload):
    if os.geteuid()==0:raise ValueError('This module must run as the intended user')
    home=pathlib.Path.home();phase=payload['phase']
    if phase=='viewer-key':
        key=home/'.ssh/family_help_demo_view_ed25519';key.parent.mkdir(mode=0o700,exist_ok=True)
        if key.is_symlink() or key.with_suffix('.pub').is_symlink():raise ValueError('Unsafe viewer key path')
        if not key.exists():subprocess.run(['/usr/bin/ssh-keygen','-q','-t','ed25519','-N','','-f',str(key),'-C','family-readonly-viewer'],check=True)
        if key.stat().st_uid!=os.getuid() or key.stat().st_mode&0o077:raise ValueError('Viewer key must be private and owned by learner')
        public=subprocess.check_output(['/usr/bin/ssh-keygen','-y','-P','','-f',str(key)],text=True).strip()
        print(json.dumps({'public_key':public}));return
    if phase=='learner-config':
        socket_dir=home/'.local/share/family-lab'
        if socket_dir.is_symlink():raise ValueError('Learning socket directory must not be a symlink')
        socket_dir.mkdir(mode=0o700,parents=True,exist_ok=True)
        if socket_dir.stat().st_uid!=os.getuid() or socket_dir.stat().st_mode&0o022:raise ValueError('Unsafe learning socket directory')
        ssh=home/'.ssh';ssh.mkdir(mode=0o700,exist_ok=True);ssh.chmod(0o700)
        keys=ssh/'authorized_keys';raw=keys.read_text() if keys.exists() else ''
        start='# BEGIN family-help managed keys\n';end='# END family-help managed keys\n'
        if raw.count(start)!=raw.count(end) or raw.count(start)>1:raise ValueError('Ambiguous managed SSH block')
        if start in raw:
            before,rest=raw.split(start,1);_,after=rest.split(end,1);raw=before+after
        # The same key elsewhere could defeat restrictions: never silently accept it.
        blobs={line.split()[1] for line in payload['public_keys'].values()}
        if any(blob in raw for blob in blobs):raise ValueError('Duplicate role key outside managed SSH block: audit before enrollment')
        lines=[]
        for role,mode in [('poll','poll'),('view','view'),('control','help')]:
            options='from="'+payload['source_ip']+'",restrict'+(',pty' if role!='poll' else '')
            lines.append(options+',command="/usr/local/libexec/family-help-child '+mode+'" '+payload['public_keys'][role])
        write(keys,raw.rstrip()+'\n'+start+'\n'.join(lines)+'\n'+end)
        for name in ('ask-dad','allow-dad','stop-dad','watch-dad','learn-with-dad'):
            local=home/'.local/bin'/name
            if local.exists() or local.is_symlink():
                if not local.is_symlink() or os.readlink(local)!='/usr/local/libexec/family-help-child':raise ValueError('Existing user command would shadow installed '+name+'; review migration explicitly')
        wants=home/'.config/systemd/user/graphical-session.target.wants';wants.mkdir(parents=True,exist_ok=True)
        link=wants/'family-help-learner.service'
        if link.exists() or link.is_symlink():
            if not link.is_symlink() or os.readlink(link)!='/etc/systemd/user/family-help-learner.service':raise ValueError('Unexpected existing learner service link')
        else:link.symlink_to('/etc/systemd/user/family-help-learner.service')
        print('Learner key roles and graphical-login service enrolled.');return
    if phase=='menu':
        path=home/'.config/omarchy/extensions/omarchy-menu.jsonc';raw=path.read_text() if path.exists() else '{}'
        clean=re.sub(r'^\s*//[^\n]*(\n|$)','',raw,flags=re.M);clean=re.sub(r',(\s*[}\]])',r'\1',clean)
        data=json.loads(clean);items=data.get('items',data)
        if not isinstance(items,dict):raise ValueError('Existing menu is not an object')
        catalog=json.loads(pathlib.Path('/usr/local/libexec/family-menu-catalog.json').read_text())
        for identifier,item in catalog.items():
            if identifier.startswith('_'):continue
            items[identifier]=dict(items.get(identifier,{}),description='Ask Dad for '+('hands-on review' if item['mode']=='manual' else 'approval'),action='omarchy-launch-floating-terminal-with-presentation /usr/local/libexec/family-menu-action '+identifier)
        for identifier,action in [('install.package','install'),('update.omarchy','update')]:
            items[identifier]=dict(items.get(identifier,{}),description='Ask Dad for approval',action='omarchy-launch-floating-terminal-with-presentation /usr/local/libexec/family-software-request '+action)
        write(path,json.dumps(data,indent=2,ensure_ascii=False)+'\n')
        print('Named software approval menu entries installed.');return
    if phase=='activate':
        runtime='/run/user/'+str(os.getuid())
        if not pathlib.Path(runtime+'/bus').exists():raise ValueError('Learner must be logged into the graphical desktop to activate; otherwise rerun activation after login')
        os.environ.update(XDG_RUNTIME_DIR=runtime,DBUS_SESSION_BUS_ADDRESS='unix:path='+runtime+'/bus',OMARCHY_PATH='/usr/share/omarchy')
        subprocess.run(['/usr/bin/systemctl','--user','daemon-reload'],check=True)
        subprocess.run(['/usr/bin/systemctl','--user','start','family-help-learner.service'],check=True)
        if payload.get('bar'):subprocess.run(['/usr/local/libexec/family-help-desktop-setup'],check=True)
        return
    raise ValueError('Unknown user setup phase')
if __name__=='__main__':main(json.loads(sys.argv[1]))
