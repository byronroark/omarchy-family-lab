#!/usr/bin/python3
"""Interactive, staged setup of the verified polling assistance deployment.

No child sudo grants, package upgrades, PAM policy or power operations.
"""
import argparse,base64,datetime,grp,hashlib,ipaddress,json,os,pathlib,pwd,re,runpy,shutil,stat,subprocess,sys,tempfile,uuid
ROOT=pathlib.Path(__file__).resolve().parents[1]
PROGRAMS=['family-help-child','family-help-dad','family-help-widget','family_help_image.py','family_identity.py','family_theme.py','family_approval.py','family_approval_client.py','family-admin-demo','family-migrate-child','family-update','family_software.py','family_menu.py','family-menu-action','family-menu-catalog.json','family-software-request','family-software-admin','family-software-execute','family-help-desktop-setup']
def selected_helper(profile):
    if 'helper' in profile:
        if 'dad' in profile or 'mom' in profile:raise ValueError('Use helper/other_parent or legacy dad/mom fields, not both')
        return profile['helper']
    return dict(profile['dad'],kind='dad',label='Dad')

def capability(profile):return selected_helper(profile).get('capability','technical')
def delegated(profile):return capability(profile)=='approver' or selected_helper(profile).get('quick_approval',False)
def expected_keys(profile):return ({'poll','view','control'} if capability(profile)=='technical' else set()) | ({'approval'} if delegated(profile) else set())
def default_approval_scope():
    catalog=json.loads((ROOT/'assistance/family-menu-catalog.json').read_text())
    return {'packages':[],'menus':sorted(name for name,item in catalog.items() if not name.startswith('_') and item['mode'] in ('package','script'))}
def validate_scope(scope):
    if not isinstance(scope,dict) or set(scope)!={'packages','menus'}:raise ValueError('Approval scope must list repository packages and named app menus')
    catalog=json.loads((ROOT/'assistance/family-menu-catalog.json').read_text())
    for name,maximum in [('packages',32),('menus',64)]:
        values=scope[name]
        if not isinstance(values,list) or len(values)>maximum or any(not isinstance(value,str) for value in values) or len(set(values))!=len(values):raise ValueError('Invalid or duplicate approval scope')
    if any(not re.fullmatch(r'[a-z0-9][a-z0-9._+-]{0,63}/[a-z0-9@_+][a-z0-9@._+-]{0,127}',value) for value in scope['packages']):raise ValueError('Use exact repository/package names in the delegated scope')
    if any(value not in catalog or catalog[value].get('mode') not in ('package','script') for value in scope['menus']):raise ValueError('Only reviewed app menus can be delegated; agents, drivers, manual actions and updates need a technical helper')
    return scope

def command_aliases(profile):
    roles={'parent',selected_helper(profile)['kind']}
    return [verb+'-'+role for role in sorted(roles) for verb in ('ask','allow','stop','watch','learn-with')]

BAD_GROUPS={'wheel','sudo','docker','disk','input','lxd','incus-admin','libvirt'}
def plain(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}',value):raise ValueError('Use an existing plain Linux login or role name')
    return value
def public_key(value):
    if not isinstance(value,str) or '\n' in value or '\r' in value:raise ValueError('Expected one Ed25519 public key')
    parts=value.split()
    if len(parts) not in (2,3) or parts[0]!='ssh-ed25519':raise ValueError('Only Ed25519 public keys are accepted')
    raw=base64.b64decode(parts[1],validate=True)
    if len(raw)!=51 or raw[:19]!=b'\0\0\0\x0bssh-ed25519\0\0\0\x20':raise ValueError('Malformed Ed25519 key')
    return ' '.join(parts[:2])
def validate(profile):
    allowed={'schema_version','learner','admin','dad','mom','public_keys','host_key','host_fingerprint','bar','helper','other_parent','approval_scope','policy_public_key','controls_timezone'}
    if not isinstance(profile,dict) or set(profile)-allowed or type(profile.get('schema_version')) is not int or profile.get('schema_version')!=1:raise ValueError('Unsupported setup profile')
    for role in ('learner','admin'):
        if not isinstance(profile.get(role),dict):raise ValueError('Missing role: '+role)
        plain(profile[role]['login'])
    if profile['learner']['login']==profile['admin']['login']:raise ValueError('Learner and administrator must be separate logins')
    learner=profile['learner'];plain(learner['id'])
    label=learner['label']
    if not isinstance(label,str) or not 1<=len(label)<=80 or not all(c.isprintable() for c in label):raise ValueError('Use a short printable learner label')
    helper=selected_helper(profile)
    if not isinstance(helper,dict) or helper.get('kind') not in ('dad','mom','parent'):raise ValueError('Choose Dad, Mom, or another parent/guardian as helper')
    plain(helper['login']);ipaddress.ip_address(helper['host'])
    label=helper.get('label')
    if not isinstance(label,str) or not 1<=len(label)<=40 or not all(c.isprintable() for c in label):raise ValueError('Use a short printable helper display label')
    if capability(profile) not in ('technical','approver'):raise ValueError('Choose technical or approver capability')
    if type(helper.get('quick_approval',False)) is not bool:raise ValueError('quick_approval must be a boolean')
    if delegated(profile):
        identifier=plain(helper.get('id'))
        if len(identifier)>20:raise ValueError('Approval parent ID must have at most 20 characters')
        validate_scope(profile.get('approval_scope'))
        if capability(profile)=='approver' and 'identity_file' in profile['admin']:raise ValueError('Approval-only profiles must not carry an administrator private-key path')
    elif 'approval_scope' in profile:raise ValueError('Delegated scope requires approval access')
    ipaddress.ip_address(profile['learner']['host'])
    if type(learner['port']) is not int or not 1<=learner['port']<=65535:raise ValueError('Invalid SSH port')
    mom=profile.get('other_parent',profile.get('mom',{'enabled':False}))
    if not isinstance(mom,dict):raise ValueError('Invalid deferred additional-parent profile')
    if mom.get('enabled') is not False:raise ValueError('A second helper is deferred; record it disabled, do not silently create access')
    if mom.get('login'):plain(mom['login'])
    if mom.get('host'):ipaddress.ip_address(mom['host'])
    if type(profile.get('bar',True)) is not bool:raise ValueError('bar must be a boolean')
    keys=profile.get('public_keys',{})
    if not isinstance(keys,dict) or set(keys)-expected_keys(profile):raise ValueError('Invalid key roles')
    for value in keys.values():public_key(value)
    if len({public_key(value) for value in keys.values()})!=len(keys):raise ValueError('SSH key roles must be independent')
    if 'identity_file' in profile['admin']:
        ssh_value(profile['admin']['identity_file'])
    if profile.get('policy_public_key'):
        policy_key=public_key(profile['policy_public_key'])
        if policy_key in {public_key(value) for value in keys.values()}:raise ValueError('Policy key must be independent of assistance and app approval keys')
        identifier=plain(helper.get('id'))
        if len(identifier)>20:raise ValueError('Policy parent ID must have at most 20 characters')
    if 'controls_timezone' in profile:
        from zoneinfo import ZoneInfo
        ZoneInfo(profile['controls_timezone'])
    if profile.get('host_key'):public_key(profile['host_key'])
    return profile

def read_profile(path):
    path=pathlib.Path(path)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as file:
        info=os.fstat(file.fileno())
        if not stat.S_ISREG(info.st_mode):raise ValueError('Enrollment profile must be a regular file')
        data=file.read(65537)
    if len(data)>65536:raise ValueError('Enrollment profile is too large')
    profile=validate(json.loads(data))
    if os.geteuid()==0:
        allowed={0,pwd.getpwnam(profile['admin']['login']).pw_uid}
        if info.st_uid not in allowed or info.st_mode&0o022:raise ValueError('Copy the enrollment JSON to a private administrator-owned file before sudo installation')
        for part in path.parents:
            st=part.lstat()
            if part.is_symlink() or st.st_uid not in allowed or st.st_mode&0o022:raise ValueError('Root enrollment requires administrator/root-owned, non-writable profile ancestors')
    return profile

def prompt_profile():
    def ask(label,default=''):
        answer=input(label+(' ['+default+']' if default else '')+': ').strip();return answer or default
    me=pwd.getpwuid(os.getuid()).pw_name
    kind=ask('Who will receive help and software-approval requests? dad / mom / parent','dad').lower()
    if kind not in ('dad','mom','parent'):raise ValueError('Choose dad, mom, or parent (another parent/guardian)')
    label=ask('What should the child call this helper?',{'dad':'Dad','mom':'Mom','parent':'Parent'}[kind])
    access=ask('Access: approver (approve/deny apps only) / technical (terminal/admin help)','approver').lower()
    if access not in ('approver','technical'):raise ValueError('Choose approver or technical')
    # Every new parent receives scoped approve/deny; technical access adds tools.
    quick=access=='technical'
    parent_id=ask('Stable approval parent ID',kind)
    profile={'schema_version':1,'learner':{'id':ask('Stable learner ID','learner-a'),'login':ask('Existing child login'),'label':ask('Private child display label','Learner'),'host':ask('Child device IP'),'port':int(ask('Child SSH port','22'))},
       'admin':{'login':ask('Existing separate parent administrator login'),**({'identity_file':ask('Administrator private key (stays on the helper PC)','~/.ssh/family_admin_ed25519')} if access=='technical' else {})},
       'helper':{'kind':kind,'label':label,'capability':access,'quick_approval':quick,**({'id':parent_id} if parent_id else {}),'login':ask(label+' desktop login',me),'host':ask(label+' device IP as seen by the child')},
       'other_parent':{'enabled':False,'login':ask('Additional parent login (optional; not enrolled)'),'host':ask('Additional parent device IP (optional; not enrolled)')},'bar':True}
    if access=='approver' or quick:
        profile['approval_scope']=default_approval_scope()
        extra=ask('Extra exact repository/package names this parent may approve (comma separated; optional)')
        profile['approval_scope']['packages']=[value.strip() for value in extra.split(',') if value.strip()]
        print('A technical administrator must review this delegated app scope on the child PC. Existing technical access is kept; updates/manual actions are not delegated.')
    profile['host_fingerprint']=ask('Child Ed25519 SHA256 fingerprint verified at its physical console (required before helper apply)')
    return validate(profile)

def run(command,**kwargs):return subprocess.run(command,check=True,**kwargs)
def fingerprint(key):return 'SHA256:'+base64.b64encode(hashlib.sha256(base64.b64decode(public_key(key).split()[1])).digest()).decode().rstrip('=')
def stamp(path):
    if path.is_symlink():return {'kind':'link','value':os.readlink(path),'uid':path.lstat().st_uid,'gid':path.lstat().st_gid}
    if not path.exists():return None
    if not path.is_file():raise ValueError('Expected a regular managed file: '+str(path))
    return {'kind':'file','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'mode':path.stat().st_mode&0o777,'uid':path.stat().st_uid,'gid':path.stat().st_gid}
class Files:
    """Atomic managed writes, drift detection, private backups, per-run rollback."""
    def __init__(self,base,state,adopt=False,staged=False):
        self.base=pathlib.Path(base);self.state=pathlib.Path(state);self.adopt=adopt;self.staged=staged;self.changes=[]
        self.previous=json.loads(self.state.read_text()).get('files',{}) if self.state.exists() else {}
        self.current=dict(self.previous);self.identifier=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
        self.backup=self.state.parent/'backups'/self.identifier
    def target(self,name):return self.base/name.lstrip('/')
    def write(self,name,data,mode=0o644,link=False):
        target=self.target(name);before=stamp(target)
        wanted={'kind':'link','value':data,'uid':os.getuid(),'gid':os.getgid()} if link else {'kind':'file','sha256':hashlib.sha256(data).hexdigest(),'mode':mode,'uid':os.getuid(),'gid':os.getgid()}
        if before==wanted:self.current[name]=wanted;return
        if before and not self.adopt and (name not in self.previous or self.previous[name]!=before):raise ValueError('Unmanaged or locally changed file; review before --adopt-existing: '+str(target))
        if not self.staged:
            for ancestor in target.parents:
                if ancestor.exists() and (ancestor.is_symlink() or ancestor.stat().st_uid not in (0,os.getuid()) or ancestor.stat().st_mode&0o022):raise ValueError('Unsafe parent directory: '+str(ancestor))
                if ancestor==self.base:break
        make_parents(target.parent, 0o755 if self.base == pathlib.Path('/') else 0o700)
        self.backup.mkdir(mode=0o700,parents=True,exist_ok=True)
        old=target.read_bytes() if before and before['kind']=='file' else None
        record={'path':name,'before':before,'after':wanted,'content':base64.b64encode(old).decode() if old is not None else None}
        self.changes.append(record)
        (self.backup/'changes.json').write_text(json.dumps(self.changes,indent=2))
        temp=target.with_name('.'+target.name+'.'+uuid.uuid4().hex)
        if link:temp.symlink_to(data)
        else:temp.write_bytes(data);temp.chmod(mode)
        os.chown(temp,os.getuid(),os.getgid(),follow_symlinks=False)
        temp.replace(target);self.current[name]=wanted
    def rollback(self):
        for item in reversed(self.changes):
            target=self.target(item['path'])
            if stamp(target)!=item['after']:raise ValueError('Rollback refused for subsequently changed file: '+str(target))
            target.unlink(missing_ok=True)
            if item['before']:
                if item['before']['kind']=='link':target.symlink_to(item['before']['value'])
                else:target.write_bytes(base64.b64decode(item['content']));target.chmod(item['before']['mode'])
                os.chown(target,item['before']['uid'],item['before']['gid'],follow_symlinks=False)
    def commit(self):
        self.state.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        value=json.dumps({'version':1,'files':self.current,'last_transaction':self.identifier},indent=2).encode()
        if self.state.exists() and json.loads(self.state.read_text()).get('files')==self.current:return
        temp=self.state.with_suffix('.tmp');temp.write_bytes(value);temp.chmod(0o600);temp.replace(self.state)

def encoded(value):return (json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode()
def learner_files(profile,uid,viewer_public,host_public,catalog=None):
    child=profile['learner']['login'];admin=profile['admin']['login'];viewer='familyviewer';home=pwd.getpwnam(child).pw_dir
    result={}
    for name in PROGRAMS:
        result['/usr/local/libexec/'+name]=((ROOT/'assistance'/name).read_bytes(),0o644 if name.endswith(('.py','.json')) else 0o755,False)
    if catalog is not None:result['/usr/local/libexec/family-menu-catalog.json']=(encoded(catalog),0o644,False)
    for name in command_aliases(profile):result['/usr/local/bin/'+name]=('/usr/local/libexec/family-help-child',0o777,True)
    result['/usr/local/sbin/family-migrate-child']=((ROOT/'assistance/family-migrate-child').read_bytes(),0o755,False)
    result['/usr/local/bin/family-update']=((ROOT/'assistance/family-update').read_bytes(),0o755,False)
    result['/etc/family-help/child.json']=(encoded({'uid':uid,'state':home+'/.local/state/family-help','socket':home+'/.local/share/family-lab/tmux.sock','session':'learning','viewer':viewer,'port':profile['learner']['port'],'helper_label':selected_helper(profile)['label'],'helper_slug':selected_helper(profile)['kind']}),0o644,False)
    result['/etc/family-help/teaching.json']=(encoded({'child':child,'admin':admin,'viewer':viewer,'helper_ip':selected_helper(profile)['host']}),0o644,False)
    result['/etc/family-help/migrations.json']=((ROOT/'assistance/reviewed-migrations.json').read_bytes(),0o644,False)
    loopback='127.0.0.1' if profile['learner']['port']==22 else '[127.0.0.1]:'+str(profile['learner']['port'])
    result['/etc/family-help/localhost_known_hosts']=((loopback+' '+public_key(host_public)+'\n').encode(),0o644,False)
    result['/etc/family-help/viewer_authorized_keys']=(('from="127.0.0.1",restrict,pty '+public_key(viewer_public)+'\n').encode(),0o644,False)
    result['/etc/ssh/sshd_config.d/40-family-help-viewer.conf']=(b'''Match User familyviewer
    AuthorizedKeysFile /etc/family-help/viewer_authorized_keys
    AuthorizedKeysCommand none
    AuthenticationMethods publickey
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    DisableForwarding yes
    PermitTTY yes
    PermitUserRC no
    ForceCommand /usr/local/libexec/family-admin-demo view
Match all
''',0o644,False)
    result['/etc/systemd/user/family-help-learner.service']=(b'''[Unit]
Description=Family Help learner consent and read-only teaching viewer
PartOf=graphical-session.target
After=graphical-session.target
[Service]
ExecStart=/usr/local/libexec/family-help-child desktop-watch
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=%t/bus
Environment=OMARCHY_PATH=/usr/share/omarchy
NoNewPrivileges=yes
Restart=on-failure
RestartSec=5
[Install]
WantedBy=graphical-session.target
''',0o644,False)
    label=selected_helper(profile)['label']
    result['/usr/local/share/applications/org.familylab.Help.desktop']=(('[Desktop Entry]\nType=Application\nName=Ask '+label+'\nExec=/usr/local/libexec/family-help-widget\nIcon=help-browser\nTerminal=false\nCategories=Utility;\n').encode(),0o644,False)
    result['/usr/local/libexec/family-software-shims/omarchy-pkg-add']=(b'#!/bin/bash\n# No installation capability in the child configuration phase.\nexec /usr/bin/pacman -Q -- "$@"\n',0o755,False)
    for name in ('manifest.json','AskDad.qml','window.lua'):
        data=(ROOT/'desktop/ask-dad'/name).read_bytes()
        if name=='AskDad.qml':data=data.decode().replace('"Ask Dad"',json.dumps('Ask '+label,ensure_ascii=True)).encode()
        if name=='manifest.json':
            manifest=json.loads(data);manifest['name']='Ask '+label;manifest['barWidget']['displayName']='Ask '+label;data=encoded(manifest)
        result['/usr/local/share/family-help/ask-dad/'+name]=(data,0o644,False)
    return result

def as_learner(account,payload):
    command=['/usr/bin/setpriv','--reuid='+str(account.pw_uid),'--regid='+str(account.pw_gid),'--init-groups','--no-new-privs','/usr/bin/env','-i','HOME='+account.pw_dir,'USER='+account.pw_name,'LOGNAME='+account.pw_name,'PATH=/usr/bin:/bin','/usr/bin/python3','-I','-c',(ROOT/'setup/user_setup.py').read_text(),json.dumps(payload)]
    return run(command,capture_output=True,text=True,cwd='/')
def groups(account):return {grp.getgrgid(gid).gr_name for gid in os.getgrouplist(account.pw_name,account.pw_gid)}
def downgrade_catalog():
    value=json.loads((ROOT/'assistance/family-menu-catalog.json').read_text());changed=[]
    for identifier,item in value.items():
        if identifier.startswith('_') or item['mode']=='manual':continue
        hashes=dict(item.get('hashes',{}))
        if item.get('script'):hashes[item['script']]=item['sha256']
        if item.get('gpu'):hashes['omarchy-install-gaming-gpu-lib32']=value['_gpu_source']['sha256']
        mismatch=False
        for name,digest in hashes.items():
            candidate=pathlib.Path('/usr/bin')/name
            if not candidate.is_file() or candidate.is_symlink() or candidate.stat().st_uid!=0 or candidate.stat().st_mode&0o022 or hashlib.sha256(candidate.read_bytes()).hexdigest()!=digest:mismatch=True;break
        if mismatch:
            original={key:item[key] for key in ('title','original')};original.update(mode='manual',packages=[],review_reason='Installed helper differs from reviewed version')
            value[identifier]=original;changed.append(identifier)
    return value,changed

def make_parents(path,mode):
    missing=[]
    while not path.exists():missing.append(path);path=path.parent
    for item in reversed(missing):item.mkdir(mode=mode);item.chmod(mode)

def trusted_system_file(path):
    for part in (path,*path.parents):
        st=part.lstat()
        if part.is_symlink() or st.st_uid!=0 or st.st_mode&0o022:raise ValueError('Unsafe root-owned assistance file: '+str(part))

def ensure_directory(path,mode):
    path=pathlib.Path(path)
    for parent in (path,*path.parents):
        if parent.exists() and (parent.is_symlink() or parent.stat().st_uid!=0 or parent.stat().st_mode&0o022):raise ValueError('Unsafe system directory: '+str(parent))
    make_parents(path,0o755);path.chmod(mode)
def check_sudo_absent(account):
    check=subprocess.run(['/usr/bin/sudo','-l','-U',account.pw_name],capture_output=True,text=True,env=dict(os.environ,LC_ALL='C'))
    if check.returncode not in (0,1) or (check.returncode==1 and 'not allowed' not in check.stdout+check.stderr):raise ValueError('Could not inspect learner sudo permissions')
    heading=re.search(r'^User '+re.escape(account.pw_name)+r' may run the following commands on [^\n]+:\s*$',check.stdout,re.M)
    if check.returncode==1 and heading is None:return
    if heading is None:raise ValueError('Unrecognized sudo permission listing; inspect sudo -l locally')
    # Accept only complete, simple denial rules. Reject positive grants, wrapped
    # continuations, mixed command lists and unfamiliar syntax rather than guessing.
    rules=[line.strip() for line in check.stdout[heading.end():].splitlines() if line.strip()]
    if not rules or any(not re.fullmatch(r'\([^()]+\)\s+!(?:ALL|/[A-Za-z0-9_./+-]+)',line) for line in rules):raise ValueError('Positive or unrecognized learner sudo rule found; inspect sudo -l locally before continuing')
def apply_learner(profile,args):
    if os.geteuid()!=0:raise ValueError('Learner installation requires private parent sudo authentication')
    if os.environ.get('SUDO_USER') not in (None,profile['admin']['login']):raise ValueError('Use the selected separate administrator')
    child=pwd.getpwnam(profile['learner']['login']);admin=pwd.getpwnam(profile['admin']['login'])
    if child.pw_uid<1000 or admin.pw_uid==0 or child.pw_uid==admin.pw_uid or groups(child)&BAD_GROUPS:raise ValueError('Learner must be a standard account, separate from the administrator; review effective privileges before setup')
    if 'wheel' not in groups(admin):raise ValueError('Choose an existing verified wheel administrator; this installer does not grant admin rights')
    if set(profile.get('public_keys',{}))!=expected_keys(profile):raise ValueError('Use the helper-generated public enrollment bundle with all independent role keys')
    for command in ('sshd','setpriv','setfacl','tmux','ssh-keygen','systemctl'):
        if not shutil.which(command):raise ValueError('Missing prerequisite: '+command+'; install it deliberately through parent administration')
    check_sudo_absent(child)
    print('Group/sudo checks passed. Broader polkit, containers and raw-device audits remain a separate prerequisite.')
    try:viewer=pwd.getpwnam('familyviewer')
    except KeyError:
        run(['/usr/bin/useradd','--system','--no-create-home','--home-dir','/var/lib/family-help-viewer','--shell','/usr/bin/bash','familyviewer']);viewer=pwd.getpwnam('familyviewer')
    if viewer.pw_uid==0 or viewer.pw_uid>=1000 or viewer.pw_dir!='/var/lib/family-help-viewer' or groups(viewer)&BAD_GROUPS:raise ValueError('Existing viewer identity is not the expected nonprivileged system role')
    status=run(['/usr/bin/passwd','-S','familyviewer'],capture_output=True,text=True).stdout.split()
    if len(status)<2 or status[1] not in ('L','LK'):raise ValueError('Viewer must have a locked password; do not reuse an ordinary account')
    for directory,mode in [('/etc/family-help',0o755),('/usr/local/libexec',0o755),('/usr/local/share/family-help/ask-dad',0o755),('/usr/local/libexec/family-software-shims',0o755),('/var/lib/family-help-viewer',0o755),('/var/lib/family-software',0o755),('/var/lib/family-software/results',0o755),('/var/lib/family-software/audit',0o700),('/var/lib/family-help-install',0o700)]:ensure_directory(directory,mode)
    viewer_public=json.loads(as_learner(child,{'phase':'viewer-key'}).stdout)['public_key']
    host_public=pathlib.Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().strip()
    catalog,changed=downgrade_catalog()
    if changed:print('Changed/unavailable installers downgraded to manual review:',', '.join(changed))
    tx=Files('/', '/var/lib/family-help-install/state.json',args.adopt_existing)
    try:
        for name,(data,mode,link) in learner_files(profile,child.pw_uid,viewer_public,host_public,catalog).items():tx.write(name,data,mode,link)
        run(['/usr/bin/sshd','-t']);verify_viewer_policy()
        print(as_learner(child,{'phase':'learner-config','source_ip':selected_helper(profile)['host'],'public_keys':profile['public_keys'],'helper_label':selected_helper(profile)['label'],'aliases':command_aliases(profile)}).stdout)
        print(as_learner(child,{'phase':'menu','helper_label':selected_helper(profile)['label']}).stdout)
        if tx.changes:run(['/usr/bin/systemctl','reload','sshd'])
        if args.activate:print(as_learner(child,{'phase':'activate','bar':profile.get('bar',True)}).stdout)
        tx.commit()
    except BaseException:
        tx.rollback()
        if subprocess.run(['/usr/bin/sshd','-t']).returncode==0:subprocess.run(['/usr/bin/systemctl','reload','sshd'])
        raise
    print('Learner setup installed. System files changed:',len(tx.changes),'; no reboot, sudoers change, package upgrade, PAM or parental-policy activation.')
    if not args.activate:print('Graphical watcher will start at the next learner graphical login. Run apply --activate after login to install/enable the bar immediately.')

def private_path(value):
    path=pathlib.Path(value).expanduser().absolute()
    if any(c in str(path) for c in '\r\n\x00'):raise ValueError('Invalid local path')
    for part in (path,*path.parents):
        if part.is_symlink():raise ValueError('Symlink in private path: '+str(part))
        if part.exists() and part.stat().st_uid not in (0,os.getuid()):raise ValueError('Unexpected private-path owner: '+str(part))
        if part.exists() and part.stat().st_mode&0o022:raise ValueError('Private path has writable ancestors: '+str(part))
    return path

def private_write(path,data):
    path=private_path(str(path));make_parents(path.parent,0o700)
    if path.exists() and path.read_bytes()==data and path.stat().st_mode&0o777==0o600:return
    temp=path.with_name('.'+path.name+'.'+uuid.uuid4().hex);temp.write_bytes(data);temp.chmod(0o600);temp.replace(path)

def check_admin_identity(value):
    path=private_path(value)
    if not path.is_file() or path.stat().st_uid!=os.getuid() or path.stat().st_mode&0o077:raise ValueError('Admin identity must be a private file owned by the selected helper')
    lines=path.read_bytes().splitlines()
    if not lines or lines[0]!=b'-----BEGIN OPENSSH PRIVATE KEY-----':raise ValueError('Use a passphrase-protected OpenSSH admin key')
    raw=base64.b64decode(b''.join(lines[1:-1]),validate=True);magic=b'openssh-key-v1\0'
    if not raw.startswith(magic) or len(raw)<len(magic)+4:raise ValueError('Malformed administrator key')
    size=int.from_bytes(raw[len(magic):len(magic)+4],'big');cipher=raw[len(magic)+4:len(magic)+4+size]
    if not cipher or cipher==b'none':raise ValueError('Administrator private key must be encrypted; use ssh-keygen -p privately first')
    return path

def pinned_host(profile):
    expected=profile.get('host_fingerprint','')
    if not re.fullmatch(r'SHA256:[A-Za-z0-9+/]{43}',expected):raise ValueError('Verify the child host fingerprint at its physical console, then record it in the profile')
    child=profile['learner']
    scan=run(['/usr/bin/ssh-keyscan','-T','5','-t','ed25519','-p',str(child['port']),child['host']],capture_output=True,text=True,timeout=10)
    found=set()
    for line in scan.stdout.splitlines():
        if line and not line.startswith('#'):
            parts=line.split()
            if len(parts)>=3:found.add(public_key(' '.join(parts[1:3])))
    matches=[key for key in found if fingerprint(key)==expected]
    if len(matches)!=1:raise ValueError('Host fingerprint mismatch; enrollment stopped. Do not accept a replacement without console verification')
    return matches[0]

def role_key(path,role):
    path=private_path(str(path));make_parents(path.parent,0o700)
    if not path.exists():run(['/usr/bin/ssh-keygen','-q','-t','ed25519','-N','','-f',str(path),'-C','family-help-'+role])
    if path.stat().st_uid!=os.getuid() or path.stat().st_mode&0o077:raise ValueError('Role key must be private and owned by the selected helper')
    return public_key(run(['/usr/bin/ssh-keygen','-y','-P','','-f',str(path)],capture_output=True,text=True).stdout.strip())

def ssh_value(value):
    if not isinstance(value,str) or any(c in value for c in '\r\n\x00%'):raise ValueError('Unsupported SSH configuration value')
    return '"'+value.replace('\\','\\\\').replace('"','\\"')+'"'

def helper_files(profile,home,identity,keys):
    config=home/'.config/family-help';learner=profile['learner'];prefix='family-'+learner['id']
    aliases={role:prefix+'-'+role for role in ('poll','view','control','admin')}
    known=config/'known_hosts';ssh_config=config/'ssh.conf'
    host=learner['host'] if learner['port']==22 else '['+learner['host']+']:'+str(learner['port'])
    lines=[]
    if delegated(profile):
        alias=prefix+'-approval-'+selected_helper(profile)['id']
        lines=['Host '+alias,'    HostName '+learner['host'],'    Port '+str(learner['port']),'    User familyap-'+selected_helper(profile)['id'],'    IdentityFile '+ssh_value(str(keys/'help-approval-ed25519')),'    UserKnownHostsFile '+ssh_value(str(known)),'    GlobalKnownHostsFile /dev/null','    StrictHostKeyChecking yes','    IdentitiesOnly yes','    IdentityAgent none','    ForwardAgent no','    ClearAllForwardings yes','    ControlMaster no','    ControlPath none','    PermitLocalCommand no','    RequestTTY no','    BatchMode yes','']
    if capability(profile)=='technical':
        for role in ('poll','view','control','admin'):
            lines+=['Host '+aliases[role], '    HostName '+learner['host'],'    Port '+str(learner['port']),
                    '    User '+(profile['admin']['login'] if role=='admin' else learner['login']),
                    '    IdentityFile '+ssh_value(str(identity if role=='admin' else keys/('help-'+role+'-ed25519'))),
                    '    UserKnownHostsFile '+ssh_value(str(known)), '    GlobalKnownHostsFile /dev/null',
                    '    StrictHostKeyChecking yes','    IdentitiesOnly yes','    ForwardAgent no','    ClearAllForwardings yes',
                    '    ControlMaster no','    ControlPath none','    PermitLocalCommand no','    BatchMode '+('no' if role=='admin' else 'yes')]
            if role!='admin':lines+=['    IdentityAgent none']
            lines+=['']
    helper_settings={'capability':capability(profile),'helper_label':selected_helper(profile)['label'],'helper_slug':selected_helper(profile)['kind'],'label':learner['label'],'ssh_config':str(ssh_config),'poll_alias':aliases['poll'],'view_alias':aliases['view'],'control_alias':aliases['control'],'admin_alias':aliases['admin']}
    if capability(profile)=='approver':
        helper_settings={key:value for key,value in helper_settings.items() if key not in ('poll_alias','view_alias','control_alias','admin_alias')}
    if delegated(profile):helper_settings.update(approval_alias=alias,quick_approval=selected_helper(profile).get('quick_approval',False))
    result={}
    for name in ('family-help-dad','family-help-widget','family_help_image.py','family_identity.py','family_theme.py','family_approval.py','family_approval_client.py','family_software.py','family_menu.py','family-menu-catalog.json'):
        result['.local/bin/'+name]=((ROOT/'assistance'/name).read_bytes(),0o644 if name.endswith(('.py','.json')) else 0o755,False)
    result['.config/family-help/ssh.conf']=('\n'.join(lines).encode(),0o600,False)
    result['.config/family-help/known_hosts']=((host+' '+profile['host_key']+'\n').encode(),0o600,False)
    result['.config/family-help/helper.json']=(encoded(helper_settings),0o600,False)
    result['.config/systemd/user/family-help-watch.service']=(('''[Unit]
Description=Family Help desktop requests
PartOf=graphical-session.target
After=graphical-session.target
[Service]
ExecStart=/usr/bin/python3 "'''+str(home/'.local/bin/family-help-dad')+'''" watch
Restart=on-failure
RestartSec=10
UMask=0077
NoNewPrivileges=yes
[Install]
WantedBy=graphical-session.target
''').encode(),0o644,False)
    result['.config/systemd/user/graphical-session.target.wants/family-help-watch.service']=(str(home/'.config/systemd/user/family-help-watch.service'),0o777,True)
    return result

def apply_helper(profile,args):
    if os.geteuid()==0 or pwd.getpwuid(os.getuid()).pw_name!=selected_helper(profile)['login']:raise ValueError('Run helper enrollment as the selected helper desktop user, without sudo')
    home=pathlib.Path.home();private_path(str(home))
    if any(c in str(home) for c in '\n\r%"\\'):raise ValueError('Unsupported home path for systemd/SSH configuration')
    identity=check_admin_identity(profile['admin']['identity_file']) if capability(profile)=='technical' else None
    existing=home/'.config/family-help/setup.json'
    if existing.exists() and json.loads(existing.read_text())['learner']['id']!=profile['learner']['id']:raise ValueError('One learner per helper profile is currently supported; do not overwrite another enrollment')
    if existing.exists() and capability(validate(json.loads(existing.read_text())))!=capability(profile):raise ValueError('Do not silently switch an existing desktop between technical and approval-only access; audit/revoke old credentials first or enroll a fresh desktop profile')
    runtime_profile=home/'.config/family-help/helper.json'
    if not runtime_profile.exists():runtime_profile=home/'.config/family-help/dad.json'
    if runtime_profile.exists() and json.loads(runtime_profile.read_text()).get('capability','technical')!=capability(profile):raise ValueError('Existing helper runtime has different access; use a fresh desktop profile or explicitly audit/revoke old access before changing roles')
    profile['host_key']=pinned_host(profile)
    keys=home/'.ssh'/('family-help-'+profile['learner']['id'])
    if capability(profile)=='approver':keys=keys/selected_helper(profile)['id']
    profile['public_keys']={role:role_key(keys/('help-'+role+'-ed25519'),role) for role in sorted(expected_keys(profile))};validate(profile)
    tx=Files(home,home/'.local/state/family-help-install/state.json',args.adopt_existing)
    try:
        for name,(data,mode,link) in helper_files(profile,home,identity,keys).items():tx.write(name,data,mode,link)
        if args.activate:
            run(['/usr/bin/systemctl','--user','daemon-reload']);run(['/usr/bin/systemctl','--user','restart','family-help-watch.service'])
        tx.commit()
    except BaseException:tx.rollback();raise
    private_write(pathlib.Path(args.profile),encoded(profile))
    if pathlib.Path(args.profile)!=existing:private_write(existing,encoded(profile))
    print('Helper enrolled; dedicated role keys remain on this helper. Root/parent key was not exported. Files changed:',len(tx.changes))
    print('Next: create the public-key enrollment bundle and install it through the separate administrator on the learner PC.')

def enrollment_bundle(profile,destination):
    if set(profile.get('public_keys',{}))!=expected_keys(profile) or not profile.get('host_key'):raise ValueError('Apply helper enrollment first to generate the restricted public keys and pin the host')
    target=private_path(destination)
    if target==ROOT or ROOT in target.parents:raise ValueError('Enrollment bundles contain private household addresses: keep them outside the checkout')
    if target.exists():raise ValueError('Choose a new bundle directory; existing bundles are never overwritten')
    make_parents(target.parent,0o700);target.mkdir(mode=0o700)
    for directory in ('assistance','setup','desktop','parental','systemd','guardian'):shutil.copytree(ROOT/directory,target/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(ROOT/'master-installation.sh',target/'master-installation.sh')
    public=json.loads(json.dumps(profile));public['admin'].pop('identity_file',None)
    private_write(target/'enrollment.json',encoded(public))
    print('Enrollment bundle created:',target)
    print('Contains public keys and private configuration; no private keys, logs or Git history. Copy this directory using your existing administrator SSH connection.')

def verify(profile,role):
    if role=='helper':
        home=pathlib.Path.home();config_path=home/'.config/family-help/helper.json'
        if not config_path.exists():config_path=home/'.config/family-help/dad.json'
        config=json.loads(config_path.read_text())
        for key in ((('poll_alias','view_alias','control_alias','admin_alias') if capability(profile)=='technical' else ()) + (('approval_alias',) if delegated(profile) else ())):
            result=run(['/usr/bin/ssh','-G','-F',config['ssh_config'],config[key]],capture_output=True,text=True).stdout
            settings=dict(line.split(' ',1) for line in result.splitlines() if ' ' in line)
            if settings.get('stricthostkeychecking')!='true' or settings.get('forwardagent')!='no':raise ValueError('Unsafe effective helper SSH settings')
        print('Local helper config and strict host checking verified. This does not prove the remote learner is enrolled or a GUI request was received.')
    else:
        if os.geteuid()!=0:raise ValueError('Learner verification needs parent sudo to inspect effective SSH policy')
        if delegated(profile):
            setup=runpy.run_path(str(ROOT/'setup/approval_setup.py'));helper=selected_helper(profile)
            setup['verify_policy'](globals(),'familyap-'+helper['id'],helper['id'])
            path=pathlib.Path('/etc/family-help/approvers.json');trusted_system_file(path)
            user=pwd.getpwnam('familyap-'+helper['id']);entry=json.loads(path.read_text())['principals'][str(user.pw_uid)]
            if not entry.get('enabled') or entry['scope']!=profile['approval_scope']:raise ValueError('Delegated parent permissions differ from the reviewed profile')
            node=pathlib.Path('/run/family-help-approval/control.sock').stat()
            if not stat.S_ISSOCK(node.st_mode) or node.st_uid!=0 or node.st_gid!=grp.getgrnam('family-help-approvers').gr_gid or node.st_mode&0o777!=0o660:raise ValueError('Approval socket permissions differ')
            print('Scoped approval SSH role, delegated scope and root/group socket permissions verified; live acceptance remains required.')
            if capability(profile)=='approver':return
        account=pwd.getpwnam(profile['learner']['login'])
        if groups(account)&BAD_GROUPS:raise ValueError('Learner has a privileged supplemental group')
        verify_viewer_policy()
        for candidate in ('/usr/local/libexec/family-software-execute','/etc/family-help/teaching.json','/etc/family-help/viewer_authorized_keys'):
            path=pathlib.Path(candidate)
            if not path.is_file() or path.is_symlink() or path.stat().st_uid!=0 or path.stat().st_mode&0o022:raise ValueError('Unsafe root helper/config: '+candidate)
        print('Learner root helpers, standard groups and effective viewer SSH restrictions verified. Complete the documented live acceptance checklist separately.')

def verify_viewer_policy():
    value=run(['/usr/bin/sshd','-T','-C','user=familyviewer,host=localhost,addr=127.0.0.1'],capture_output=True,text=True).stdout
    fields={key.lower():setting for line in value.splitlines() if ' ' in line for key,setting in [line.split(' ',1)]}
    expected={'forcecommand':'/usr/local/libexec/family-admin-demo view','authorizedkeysfile':'/etc/family-help/viewer_authorized_keys','passwordauthentication':'no','kbdinteractiveauthentication':'no','disableforwarding':'yes','permituserrc':'no','permittty':'yes','authenticationmethods':'publickey','authorizedkeyscommand':'none'}
    if any(fields.get(key)!=value for key,value in expected.items()):raise ValueError('Effective SSH viewer policy differs from the forced, read-only role; inspect earlier Match/global directives')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('configure','plan','apply','bundle','verify','controls'),nargs='?',default='plan')
    parser.add_argument('--role',choices=('helper','learner'),default='helper')
    parser.add_argument('--profile',default=str(pathlib.Path.home()/'.config/family-help/setup.json'))
    parser.add_argument('--out',help='New private directory outside the repository for bundle')
    parser.add_argument('--approval-only',action='store_true',help='Refuse any technical-role profile; use when a technical parent installs another parent’s data-only enrollment')
    parser.add_argument('--approval-transport-only',action='store_true',help='Enroll only the scoped approval endpoint on an existing learner setup, preserving technical keys and desktop configuration')
    parser.add_argument('--enable-pam',action='store_true',help='Controls enrollment only: install login and normal-lock policy gates, without enabling enforcement')
    parser.add_argument('--activate',action='store_true',help='Start graphical services now; requires the intended desktop session')
    parser.add_argument('--adopt-existing',action='store_true',help='Explicitly replace reviewed existing managed files, preserving private backups')
    args=parser.parse_args();os.umask(0o077)
    if args.approval_transport_only and (args.command!='apply' or args.role!='learner'):raise ValueError('--approval-transport-only is only for apply --role learner')
    args.profile=str(pathlib.Path(args.profile).expanduser().absolute())
    # Configuration is intentionally outside Git: IPs and family names are private.
    if pathlib.Path(args.profile)==ROOT or ROOT in pathlib.Path(args.profile).parents:raise ValueError('Keep the private setup profile outside the checkout')
    if args.command=='configure':
        if args.role!='helper' or os.geteuid()==0:raise ValueError('Configure interactively as the selected helper desktop user')
        if pathlib.Path(args.profile).exists():raise ValueError('Existing profile preserved; edit it privately or choose another --profile path')
        profile=prompt_profile()
        if args.approval_only and capability(profile)!='approver':raise ValueError('This command is restricted to an approval-only profile')
        private_write(pathlib.Path(args.profile),encoded(profile));print('Private profile saved:',args.profile);return
    profile=read_profile(args.profile)
    if args.approval_only and capability(profile)!='approver':raise ValueError('This command is restricted to an approval-only profile')
    if args.command=='controls':
        module=runpy.run_path(str(ROOT/'setup/policy_setup.py'))
        if args.role=='helper':module['enroll_helper'](globals(),profile,args)
        else:
            local=public_key(pathlib.Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().strip())
            if local!=public_key(profile.get('host_key','')) or fingerprint(local)!=profile.get('host_fingerprint'):raise ValueError('Enrollment profile belongs to a different learner host')
            module['install'](globals(),profile,args)
        return
    if args.enable_pam:raise ValueError('--enable-pam is only for the controls enrollment command')
    if args.command=='plan':
        print('Read-only enrollment plan:')
        print(json.dumps({'learner':profile['learner'],'helper':selected_helper(profile),'other_parent':profile.get('other_parent',profile.get('mom',{'enabled':False}))},indent=2))
        print('Capability:',capability(profile))
        if capability(profile)=='technical' and delegated(profile):print('Quick approvals enabled for explicitly reviewed scope:',json.dumps(profile['approval_scope']))
        print('Administrator:',profile['admin']['login'])
        if capability(profile)=='approver':
            print('Approval-only: own restricted key; no admin, view or control credentials. Existing technical helper is preserved. Root socket worker executes only exact approved app plans.')
            print('Technical administrator must review scope:',json.dumps(profile['approval_scope']))
            return
        print('Helper: encrypted administrator key stays local; pin host key; create independent forced poll/view/consent keys; install desktop watcher.')
        print('Learner: require standard child + existing administrator; add locked read-only system viewer; root-owned approval/migration helpers; child-owned menus, widget and optional top-right icon.')
        print('Never: give child sudo, run arbitrary child commands as root, activate experimental parental policy, enroll a second helper, upgrade packages, reboot, change firewall or enable helper SSH.')
        return
    if args.command=='apply':
        if args.role=='helper':apply_helper(profile,args)
        else:
            local=public_key(pathlib.Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().strip())
            if local!=public_key(profile.get('host_key','')) or fingerprint(local)!=profile.get('host_fingerprint'):raise ValueError('Enrollment bundle belongs to a different learner host')
            if args.approval_transport_only and not delegated(profile):raise ValueError('Approval transport requires an explicitly scoped enrollment')
            if capability(profile)=='technical' and not args.approval_transport_only:apply_learner(profile,args)
            if delegated(profile):runpy.run_path(str(ROOT/'setup/approval_setup.py'))['install'](globals(),profile,args)
    elif args.command=='bundle':
        if not args.out:raise ValueError('bundle requires --out outside the repository')
        enrollment_bundle(profile,args.out)
    else:verify(profile,args.role)
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:sys.exit('Enrollment stopped: '+str(exc))
