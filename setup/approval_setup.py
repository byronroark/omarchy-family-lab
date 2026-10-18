"""Scoped approval transport enrollment; never replaces technical help keys."""
import grp,json,os,pathlib,pwd,subprocess
GROUP='family-help-approvers'
SOCKET=b'''[Unit]
Description=Restricted family approval endpoint
[Socket]
ListenStream=/run/family-help-approval/control.sock
SocketUser=root
SocketGroup=family-help-approvers
SocketMode=0660
DirectoryMode=0755
RemoveOnStop=yes
[Install]
WantedBy=sockets.target
'''
SERVICE=b'''[Unit]
Description=Root-owned delegated family app-install worker
Requires=family-help-approval.socket
After=family-help-approval.socket
[Service]
Type=simple
ExecStart=/usr/bin/python3 -E -s /usr/local/libexec/family-approval-worker
ExecReload=/usr/bin/kill -HUP $MAINPID
User=root
Group=root
UMask=0077
NoNewPrivileges=yes
Restart=on-failure
RestartSec=5
KillMode=control-group
TimeoutStopSec=30
'''
def desired_files(api,profile,uid,registry):
    helper=api['selected_helper'](profile);identifier=helper['id'];account='familyap-'+identifier
    registry=json.loads(json.dumps(registry));principals=registry['principals']
    if str(uid) in principals and principals[str(uid)]['id']!=identifier:raise ValueError('Transport UID is enrolled for another parent')
    if any(item['id']==identifier and user!=str(uid) for user,item in principals.items()):raise ValueError('Parent transport UID changed; audit before re-enrollment')
    scope=profile['approval_scope']
    principals[str(uid)]={'id':identifier,'label':helper['label'],'enabled':True,'scope':scope}
    result={}
    for name in ('family_approval.py','family_approval_actions.py','family-approval-bridge','family-approval-worker'):
        result['/usr/local/libexec/'+name]=((api['ROOT']/'assistance'/name).read_bytes(),0o644 if name.endswith('.py') else 0o755,False)
    result['/etc/family-help/approvers.json']=(api['encoded'](registry),0o600,False)
    key='from="'+helper['host']+'",restrict '+api['public_key'](profile['public_keys']['approval'])+'\n'
    result['/etc/family-help/approvers/'+identifier+'.keys']=(key.encode(),0o644,False)
    ssh=f'''Match User {account}
    AuthorizedKeysFile /etc/family-help/approvers/{identifier}.keys
    AuthorizedKeysCommand none
    AuthenticationMethods publickey
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    DisableForwarding yes
    PermitTTY no
    PermitUserRC no
    PermitUserEnvironment no
    ForceCommand /usr/local/libexec/family-approval-bridge
Match all
'''
    result['/etc/ssh/sshd_config.d/41-family-help-'+identifier+'.conf']=(ssh.encode(),0o644,False)
    result['/etc/systemd/system/family-help-approval.socket']=(SOCKET,0o644,False)
    result['/etc/systemd/system/family-help-approval.service']=(SERVICE,0o644,False)
    return result

def verify_policy(api,account,identifier):
    output=api['run'](['/usr/bin/sshd','-T','-C','user='+account+',host=localhost,addr=127.0.0.1'],capture_output=True,text=True).stdout
    effective=dict(line.split(' ',1) for line in output.splitlines() if ' ' in line)
    expected={'forcecommand':'/usr/local/libexec/family-approval-bridge','authorizedkeysfile':'/etc/family-help/approvers/'+identifier+'.keys','authenticationmethods':'publickey','passwordauthentication':'no','kbdinteractiveauthentication':'no','permittty':'no','disableforwarding':'yes','permituserrc':'no','permituserenvironment':'no','authorizedkeyscommand':'none'}
    if any(effective.get(name)!=value for name,value in expected.items()):raise ValueError('Effective approval transport SSH policy is not restricted as expected')

def install(api,profile,args):
    helper=api['selected_helper'](profile);identifier=helper['id'];account='familyap-'+identifier
    if os.geteuid()!=0 or os.environ.get('SUDO_USER') not in (None,profile['admin']['login']):raise ValueError('Use the existing separate parent administrator to enroll delegated access')
    teaching_path=pathlib.Path('/etc/family-help/teaching.json');api['trusted_system_file'](teaching_path)
    teaching=json.loads(teaching_path.read_text())
    if teaching['child']!=profile['learner']['login'] or teaching['admin']!=profile['admin']['login']:raise ValueError('Approval enrollment must match the already installed learner/administrator')
    child=pwd.getpwnam(teaching['child'])
    if child.pw_uid<1000 or api['groups'](child)&(api['BAD_GROUPS']|{GROUP}):raise ValueError('Learner must remain a standard account without approval transport membership')
    api['check_sudo_absent'](child)
    # Do not replace the running technical deployment. Require its reviewed APIs.
    for name in ('family_software.py','family_menu.py'):
        installed=pathlib.Path('/usr/local/libexec')/name;api['trusted_system_file'](installed)
        if installed.read_bytes()!=(api['ROOT']/'assistance'/name).read_bytes():raise ValueError('Installed assistance API differs; technical helper must reconcile it before approval-only enrollment')
    if not api['delegated'](profile) or set(profile.get('public_keys',{}))!=api['expected_keys'](profile):raise ValueError('Use a complete helper bundle with explicitly scoped approval access')
    try:grp.getgrnam(GROUP)
    except KeyError:api['run'](['/usr/bin/groupadd','--system',GROUP])
    home='/var/lib/family-approvers/'+identifier
    try:user=pwd.getpwnam(account)
    except KeyError:
        api['run'](['/usr/bin/useradd','--system','--user-group','--no-create-home','--home-dir',home,'--shell','/usr/bin/bash','--groups',GROUP,account]);user=pwd.getpwnam(account)
    if not 0<user.pw_uid<1000 or user.pw_dir!=home or not api['groups'](user)<={account,GROUP} or GROUP not in api['groups'](user):raise ValueError('Approval transport is not the expected isolated system account')
    api['check_sudo_absent'](user)
    for name in {teaching['child'],teaching['admin'],teaching.get('viewer','familyviewer')}:
        if pwd.getpwnam(name).pw_uid==user.pw_uid:raise ValueError('Approval transport UID must be separate from learner, administrator and viewer')
    status=api['run'](['/usr/bin/passwd','-S',account],capture_output=True,text=True).stdout.split()
    if len(status)<2 or status[1] not in ('L','LK'):raise ValueError('Approval transport must have a locked password')
    # No user-owned startup file or authorized_keys can override forced SSH policy.
    for directory,mode in [(home,0o755),('/etc/family-help/approvers',0o755),('/var/lib/family-software',0o755),('/var/lib/family-software/results',0o755),('/var/lib/family-software/audit',0o700),('/var/lib/family-software/approval-reviews',0o700),('/var/lib/family-software/approval-jobs',0o700),('/var/lib/family-help-install',0o700)]:api['ensure_directory'](directory,mode)
    registry_path=pathlib.Path('/etc/family-help/approvers.json')
    registry={'version':1,'principals':{}}
    if registry_path.exists():api['trusted_system_file'](registry_path);registry=json.loads(registry_path.read_text())
    if set(registry)!={'version','principals'} or registry['version']!=1 or not isinstance(registry['principals'],dict):raise ValueError('Unknown approval registry')
    socket_was_active=subprocess.run(['/usr/bin/systemctl','is-active','--quiet','family-help-approval.socket']).returncode==0
    service_was_active=subprocess.run(['/usr/bin/systemctl','is-active','--quiet','family-help-approval.service']).returncode==0
    tx=api['Files']('/', '/var/lib/family-help-install/approvers-state.json',args.adopt_existing)
    try:
        for name,(data,mode,link) in desired_files(api,profile,user.pw_uid,registry).items():tx.write(name,data,mode,link)
        api['run'](['/usr/bin/sshd','-t']);verify_policy(api,account,identifier)
        api['run'](['/usr/bin/systemctl','daemon-reload'])
        api['run'](['/usr/bin/systemctl','enable','--now','family-help-approval.socket'])
        if subprocess.run(['/usr/bin/systemctl','is-active','--quiet','family-help-approval.service']).returncode==0:api['run'](['/usr/bin/systemctl','reload','family-help-approval.service'])
        api['run'](['/usr/bin/systemctl','reload','sshd']);tx.commit()
    except BaseException:
        if not socket_was_active:subprocess.run(['/usr/bin/systemctl','disable','--now','family-help-approval.socket'])
        if not service_was_active:subprocess.run(['/usr/bin/systemctl','stop','family-help-approval.service'])
        tx.rollback();subprocess.run(['/usr/bin/systemctl','daemon-reload'])
        if subprocess.run(['/usr/bin/sshd','-t']).returncode==0:subprocess.run(['/usr/bin/systemctl','reload','sshd'])
        raise
    print('Scoped approval access enrolled:',helper['label'],'; root files changed:',len(tx.changes))
    print('Existing technical helper, learner menu, keys and desktop configuration were preserved. No sudoers grant or administrator credential was added.')
    print('Delegated menu scope:',', '.join(profile['approval_scope']['menus']))
    print('Delegated repository packages:',', '.join(profile['approval_scope']['packages']) or '(none beyond the named menu scope)')
