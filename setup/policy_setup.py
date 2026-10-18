"""Independent policy enrollment; new policies stay off until reviewed by a parent."""
import grp,hashlib,json,os,pathlib,pwd,subprocess
from zoneinfo import ZoneInfo

def enroll_helper(api,profile,args):
    helper=api['selected_helper'](profile);identifier=api['plain'](helper.get('id'))
    if len(identifier)>20:raise ValueError('Policy parent ID must have at most 20 characters')
    if os.geteuid()==0 or pwd.getpwuid(os.getuid()).pw_name!=helper['login']:raise ValueError('Enroll controls as the helper desktop login without sudo')
    home=pathlib.Path.home()
    if any(char in str(home) for char in '\n\r%"\\'):raise ValueError('Unsupported home path for desktop configuration')
    folder=home/'.config/family-help';runtime=folder/'helper.json'
    if not runtime.exists():runtime=folder/'dad.json'
    config=json.loads(runtime.read_text());api['private_path'](str(runtime))
    if api['pinned_host'](profile)!=api['public_key'](profile['host_key']):raise ValueError('Learner host changed')
    key=home/'.ssh'/('family-policy-'+profile['learner']['id'])/(identifier+'-ed25519')
    profile['policy_public_key']=api['role_key'](key,'policy-'+identifier)
    alias='family-'+profile['learner']['id']+'-policy-'+identifier
    ssh=pathlib.Path(config['ssh_config']);api['private_path'](str(ssh));text=ssh.read_text()
    start='# BEGIN family-policy '+identifier+'\n';end='# END family-policy '+identifier+'\n'
    if text.count(start)!=text.count(end) or text.count(start)>1:raise ValueError('Ambiguous policy SSH block')
    if start in text:
        before,rest=text.split(start,1);_,after=rest.split(end,1);text=before+after
    if alias in text:raise ValueError('Policy alias already exists outside its managed block')
    child=profile['learner']
    lines=['Host '+alias,'    HostName '+child['host'],'    Port '+str(child['port']),'    User flpolicy-'+identifier,'    IdentityFile '+api['ssh_value'](str(key)),'    UserKnownHostsFile '+api['ssh_value'](str(folder/'known_hosts')),'    GlobalKnownHostsFile /dev/null','    StrictHostKeyChecking yes','    IdentitiesOnly yes','    IdentityAgent none','    ForwardAgent no','    ClearAllForwardings yes','    ControlMaster no','    ControlPath none','    PermitLocalCommand no','    RequestTTY no','    BatchMode yes']
    config.update(policy_alias=alias,policy_peer=child['id'])
    tx=api['Files'](home,home/'.local/state/family-help-install/policy-helper.json',args.adopt_existing)
    try:
        for name in ('family_policy_client.py','family-time-widget','family-help-dad','family-help-widget','family_identity.py'):
            tx.write('.local/bin/'+name,(api['ROOT']/'assistance'/name).read_bytes(),0o644 if name.endswith('.py') else 0o755)
        tx.write(str(ssh.relative_to(home)),(text.rstrip()+'\n'+start+'\n'.join(lines)+'\n'+end).encode(),0o600)
        tx.write('.config/family-help/helper.json',api['encoded'](config),0o600)
        tx.write('.local/share/applications/org.familylab.Time.desktop',('[Desktop Entry]\nType=Application\nName=Family breaks and bedtime\nExec="'+str(home/'.local/bin/family-time-widget')+'"\nIcon=preferences-system-time\nTerminal=false\nCategories=Settings;\n').encode(),0o644)
        tx.commit()
    except BaseException:tx.rollback();raise
    api['private_write'](pathlib.Path(args.profile),api['encoded'](profile))
    if args.activate:api['run'](['/usr/bin/systemctl','--user','restart','family-help-watch.service'])
    print('Parent controls staged. Policy key is separate from approval, help and administrator credentials. Copy enrollment JSON through the existing administrator route.')

def account(api,name,home,group=None):
    try:user=pwd.getpwnam(name)
    except KeyError:
        command=['/usr/bin/useradd','--system','--user-group','--no-create-home','--home-dir',home,'--shell','/usr/bin/bash' if group else '/usr/bin/nologin']
        if group:command+=['--groups',group]
        api['run'](command+[name]);user=pwd.getpwnam(name)
    wanted={name}|({group} if group else set())
    if not 0<user.pw_uid<1000 or user.pw_dir!=home or api['groups'](user)!=wanted:raise ValueError('Unexpected policy/guard system account privileges')
    api['check_sudo_absent'](user)
    status=api['run'](['/usr/bin/passwd','-S',name],capture_output=True,text=True).stdout.split()
    if len(status)<2 or status[1] not in ('L','LK'):raise ValueError('Policy/guard system account must have a locked password')
    api['ensure_directory'](home,0o755);return user

def install(api,profile,args):
    helper=api['selected_helper'](profile);identifier=api['plain'](helper.get('id'));peer=profile['learner']['id'];child=pwd.getpwnam(profile['learner']['login'])
    if os.geteuid()!=0 or os.environ.get('SUDO_USER') not in (None,profile['admin']['login']):raise ValueError('Use the separate parent administrator for controls enrollment')
    api['public_key'](profile.get('policy_public_key',''))
    if child.pw_uid<1000 or api['groups'](child)&api['BAD_GROUPS']:raise ValueError('Learner must be a standard account')
    api['check_sudo_absent'](child)
    for directory,mode in [('/etc/family-lab',0o755),('/var/lib/family-lab',0o700),('/var/lib/family-help-install',0o700),('/usr/local/share/family-lab',0o755),('/usr/local/share/family-lab/guard',0o755),('/usr/local/share/family-lab/guard/Dino',0o755)]:api['ensure_directory'](directory,mode)
    try:grp.getgrnam('family-lab-parents')
    except KeyError:api['run'](['/usr/bin/groupadd','--system','family-lab-parents'])
    parent=account(api,'flpolicy-'+identifier,'/var/lib/family-policy/'+identifier,'family-lab-parents')
    guard_name='flguard-'+hashlib.sha256(peer.encode()).hexdigest()[:12];guard=account(api,guard_name,'/var/lib/family-guards/'+peer)
    if len({parent.pw_uid,guard.pw_uid,child.pw_uid,pwd.getpwnam(profile['admin']['login']).pw_uid})!=4:raise ValueError('Control identities must be distinct')
    config_path=pathlib.Path('/etc/family-lab/enrollment.json');config={'subjects':{},'parents':{},'browsers':[],'guards':{},'parent_helpers':{}}
    if config_path.exists():api['trusted_system_file'](config_path);config=json.loads(config_path.read_text())
    enrollment={'uid':child.pw_uid,'login':child.pw_name}
    if config['subjects'].get(peer,enrollment)!=enrollment or any(row['uid']==child.pw_uid and name!=peer for name,row in config['subjects'].items()):raise ValueError('Learner enrollment conflicts')
    policy_path=pathlib.Path('/var/lib/family-lab/policy.json')
    if policy_path.exists():
        api['trusted_system_file'](policy_path)
        if any(item['mode']=='enforce' for item in json.loads(policy_path.read_text())['policy']['subjects'].values()):raise ValueError('Switch enforced policies off and release their guard before upgrading controls')
    if policy_path.exists() and peer not in config['subjects']:raise ValueError('Adding a learner requires a reviewed policy migration')
    if str(parent.pw_uid) in config['parents'] and config['parents'][str(parent.pw_uid)]!=helper['label']:raise ValueError('Policy parent UID is already enrolled differently')
    if str(guard.pw_uid) in config.get('guards',{}) and config['guards'][str(guard.pw_uid)]!=peer:raise ValueError('Guard UID belongs to another learner')
    config.setdefault('time_models',{})[peer]='protected-breaks'
    config['subjects'][peer]=enrollment;config['parents'][str(parent.pw_uid)]=helper['label'];config.setdefault('guards',{})[str(guard.pw_uid)]=peer
    slug=helper['kind'];routes=config.setdefault('parent_helpers',{})
    if slug in routes and routes[slug]!=parent.pw_uid:raise ValueError('A different parent already uses this helper button')
    routes[slug]=parent.pw_uid
    if set(config['guards'])&set(config['parents']) or any(str(row['uid']) in set(config['guards'])|set(config['parents']) for row in config['subjects'].values()):raise ValueError('Learner, guard and parent authorizations must be separate')
    tx=api['Files']('/', '/var/lib/family-help-install/policy-system.json',args.adopt_existing)
    status_path=pathlib.Path('/run/family-lab/status.json')
    if status_path.exists():
        api['trusted_system_file'](status_path)
        if any(row.get('guard_covering') for row in json.loads(status_path.read_text())['subjects'].values()):raise ValueError('Release the protected guard before upgrading its service or enrollment')
    service_was_active=subprocess.run(['/usr/bin/systemctl','is-active','--quiet','family-lab-policy.service']).returncode==0
    if service_was_active:
        response=api['run'](['/usr/local/libexec/family-lab-policy','local','{"op":"guard-active"}'],capture_output=True,text=True,timeout=5).stdout
        if json.loads(response).get('active') is not False:raise ValueError('Release the active guard before upgrading controls')
    try:
        tx.write('/etc/family-lab/enrollment.json',api['encoded'](config),0o644)
        for name in ('family-lab-policy','family_breaks.py','family_guard.py'):tx.write('/usr/local/libexec/'+name,(api['ROOT']/'parental'/name).read_bytes(),0o644 if name.endswith('.py') else 0o755)
        tx.write('/etc/systemd/user/family-time-warnings.service',('[Unit]\nDescription=Family break and bedtime warnings\nPartOf=graphical-session.target\nAfter=graphical-session.target\nConditionUser='+child.pw_name+'\n[Service]\nExecStart=/usr/local/libexec/family-lab-policy watch\nEnvironment=DBUS_SESSION_BUS_ADDRESS=unix:path=%t/bus\nRestart=on-failure\nRestartSec=5\nNoNewPrivileges=yes\n[Install]\nWantedBy=graphical-session.target\n').encode())
        tx.write('/etc/systemd/user/graphical-session.target.wants/family-time-warnings.service','/etc/systemd/user/family-time-warnings.service',0o777,True)
        tx.write('/etc/systemd/system/family-lab-policy.service',(api['ROOT']/'systemd/family-lab-policy.service').read_bytes())
        for source,target in [('BreakCard.qml','Dino/BreakCard.qml'),('PixelDino.qml','Dino/PixelDino.qml'),('guard/shell.qml','shell.qml')]:tx.write('/usr/local/share/family-lab/guard/'+target,(api['ROOT']/'guardian'/source).read_bytes())
        key_path='/etc/family-lab/policy-'+identifier+'.keys';tx.write(key_path,('from="'+helper['host']+'",restrict '+api['public_key'](profile['policy_public_key'])+'\n').encode())
        match='Match User '+parent.pw_name+'\n    AuthorizedKeysFile '+key_path+'\n    AuthorizedKeysCommand none\n    AuthenticationMethods publickey\n    PasswordAuthentication no\n    KbdInteractiveAuthentication no\n    DisableForwarding yes\n    PermitTTY no\n    PermitUserRC no\n    ForceCommand /usr/local/libexec/family-lab-policy remote\nMatch all\n'
        tx.write('/etc/ssh/sshd_config.d/42-family-policy-'+identifier+'.conf',match.encode())
        if not policy_path.exists():
            import importlib.machinery,importlib.util
            loader=importlib.machinery.SourceFileLoader('new_policy',str(api['ROOT']/'parental/family-lab-policy'));spec=importlib.util.spec_from_loader(loader.name,loader);module=importlib.util.module_from_spec(spec);loader.exec_module(module)
            policy=module.defaults(config['subjects']);policy['timezone']=profile.get('controls_timezone','UTC');ZoneInfo(policy['timezone'])
            for name,item in policy['subjects'].items():item.update(name=profile['learner']['label'] if name==peer else name,breaks={'enabled':True,'use_minutes':60,'break_minutes':15},hours={day:[['00:00','24:00']] for day in module.DAYS})
            tx.write('/var/lib/family-lab/policy.json',api['encoded']({'revision':0,'policy':policy}),0o600)
            tx.write('/etc/family-lab/gate.json',api['encoded']({'subjects':{str(row['uid']):False for row in config['subjects'].values()}}),0o644)
        if args.enable_pam:
            for name,stage,operation in [('system-login','account','login-check'),('omarchy-lock-password','auth','unlock-check'),('omarchy-lock-fingerprint','auth','unlock-check')]:
                path=pathlib.Path('/etc/pam.d')/name
                if not path.exists() and name=='omarchy-lock-fingerprint':continue
                api['trusted_system_file'](path);original=path.read_text();line=stage+' requisite pam_exec.so quiet /usr/local/libexec/family-lab-policy '+operation+'\n'
                if stage not in original:raise ValueError('Unrecognized PAM layout: '+name)
                if line not in original:
                    backup='/etc/family-lab/'+name+'.before-controls'
                    if pathlib.Path(backup).exists():raise ValueError('PAM backup already exists; inspect changes')
                    tx.write(backup,original.encode(),0o600);tx.write(str(path),(line+original).encode())
            tx.write('/etc/family-lab/pam-ready',b'Root gates installed; verify real login and resume before guard acceptance.\n')
        api['run'](['/usr/bin/sshd','-t'])
        output=api['run'](['/usr/bin/sshd','-T','-C','user='+parent.pw_name+',host=localhost,addr='+helper['host']],capture_output=True,text=True).stdout
        fields={key.lower():value for line in output.splitlines() if ' ' in line for key,value in [line.split(' ',1)]}
        expected={'forcecommand':'/usr/local/libexec/family-lab-policy remote','authorizedkeysfile':key_path,'permittty':'no','disableforwarding':'yes','permituserrc':'no','permituserenvironment':'no','passwordauthentication':'no','kbdinteractiveauthentication':'no','authenticationmethods':'publickey','authorizedkeyscommand':'none'}
        if any(fields.get(key)!=value for key,value in expected.items()):raise ValueError('Unsafe effective policy SSH settings')
        api['run'](['/usr/bin/systemctl','daemon-reload']);api['run'](['/usr/bin/systemctl','reload','sshd'])
        if args.activate:
            api['run'](['/usr/bin/systemctl','enable','--now','family-lab-policy.service'])
            if service_was_active and tx.changes:api['run'](['/usr/bin/systemctl','restart','family-lab-policy.service'])
            user_command=['/usr/bin/setpriv','--reuid='+str(child.pw_uid),'--regid='+str(child.pw_gid),'--init-groups','--no-new-privs','/usr/bin/env','-i','HOME='+child.pw_dir,'USER='+child.pw_name,'PATH=/usr/bin:/bin','XDG_RUNTIME_DIR=/run/user/'+str(child.pw_uid),'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/'+str(child.pw_uid)+'/bus','/usr/bin/systemctl','--user']
            api['run'](user_command+['daemon-reload']);api['run'](user_command+['start','family-time-warnings.service'])
        tx.commit()
    except BaseException:
        if not service_was_active:subprocess.run(['/usr/bin/systemctl','disable','--now','family-lab-policy.service'])
        tx.rollback();subprocess.run(['/usr/bin/systemctl','daemon-reload'])
        if subprocess.run(['/usr/bin/sshd','-t']).returncode==0:subprocess.run(['/usr/bin/systemctl','reload','sshd'])
        raise
    print('Controls enrolled. New policy is OFF, with 60-minute use / 15-minute break defaults. No guard acceptance marker or enforcement was enabled.')
