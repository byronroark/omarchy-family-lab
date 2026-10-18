#!/usr/bin/python3
"""Isolated enrollment tests: no SSH, sudo, accounts, services or live config writes."""
import base64,copy,importlib.util,json,os,pathlib,subprocess,tempfile,types,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('enrollment',ROOT/'setup/family_install.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def key(number):return 'ssh-ed25519 '+base64.b64encode(b'\0\0\0\x0bssh-ed25519\0\0\0\x20'+bytes([number])*32).decode()
def profile():return {'schema_version':1,'learner':{'login':'learner','id':'learner-a','label':'Learner A','host':'192.0.2.10','port':22},'admin':{'login':'parent','identity_file':'/not-read/admin-key'},'dad':{'login':'helper','host':'192.0.2.20'},'mom':{'enabled':False,'login':'otherparent','host':'192.0.2.30'},'bar':True,'public_keys':{name:key(i) for i,name in enumerate(('poll','view','control'),1)},'host_key':key(4),'host_fingerprint':m.fingerprint(key(4))}
class Enrollment(unittest.TestCase):
    def test_profile_boundaries(self):
        m.validate(profile())
        cases=[]
        for role,field,value in [('learner','login','name;id'),('learner','port',True),('dad','host','host;command'),('mom','enabled',True)]:
            p=profile();p[role][field]=value;cases.append(p)
        p=profile();p['admin']['login']='learner';cases.append(p)
        p=profile();p['public_keys']['view']=p['public_keys']['poll']+' different-comment';cases.append(p)
        p=profile();p['public_keys']['view']='command="shell" '+key(1);cases.append(p)
        for p in cases:
            with self.assertRaises((ValueError,KeyError)):m.validate(p)
    def test_technical_quick_approval_has_separate_transport(self):
        p=profile();p.pop('dad');p.pop('mom')
        p['helper']={'kind':'mom','label':'Mom','login':'helper','host':'192.0.2.20','capability':'technical','id':'mom','quick_approval':True}
        p['approval_scope']={'packages':['extra/jq'],'menus':[]};p['public_keys']['approval']=key(9);m.validate(p)
        self.assertEqual(m.expected_keys(p),{'poll','view','control','approval'})
        files=m.helper_files(p,pathlib.Path('/home/helper'),pathlib.Path('/home/helper/admin'),pathlib.Path('/home/helper/roles'))
        cfg=json.loads(files['.config/family-help/helper.json'][0]);ssh=files['.config/family-help/ssh.conf'][0].decode()
        self.assertTrue(cfg['quick_approval']);self.assertEqual(cfg['capability'],'technical')
        self.assertEqual(ssh.count('Host '),5);self.assertIn('admin_alias',cfg)
        approval=ssh.split('Host '+cfg['approval_alias']+'\n')[1].split('Host ')[0]
        self.assertIn('User familyap-mom',approval);self.assertIn('help-approval-ed25519',approval)
        self.assertIn('IdentityAgent none',approval);self.assertIn('RequestTTY no',approval);self.assertIn('BatchMode yes',approval)
        self.assertNotIn('/home/helper/admin',approval)
        for change in ({'quick_approval':'yes'},{'id':'x'*21},{'quick_approval':False}):
            bad=copy.deepcopy(p);bad['helper'].update(change)
            with self.assertRaises(ValueError):m.validate(bad)
    def test_endpoint_only_dispatch_preserves_technical_deployment(self):
        p=profile();p.pop('dad');p.pop('mom')
        p['helper']={'kind':'dad','label':'Dad','login':'helper','host':'192.0.2.20','capability':'technical','id':'dad','quick_approval':True}
        p['approval_scope']={'packages':[],'menus':[]};p['public_keys']['approval']=key(9)
        for endpoint_only in (True,False):
            argv=['master','apply','--role','learner','--profile','/private/enrollment.json']+(['--approval-transport-only'] if endpoint_only else [])
            with self.subTest(endpoint_only=endpoint_only),patch.object(m.sys,'argv',argv),patch.object(m,'read_profile',return_value=p),patch.object(m.pathlib.Path,'read_text',return_value=key(4)),patch.object(m,'apply_learner') as base,patch.object(m.runpy,'run_path',return_value={'install':lambda api,profile,args:None}) as transport:
                m.main()
                self.assertEqual(base.call_count,0 if endpoint_only else 1);transport.assert_called_once()
    def test_new_technical_enrollment_includes_quick_approval_by_default(self):
        answers=iter(['mom','','technical','','','learner','','192.0.2.10','','parent','/not-read/admin-key','','192.0.2.20','','','','SHA256:'+('A'*43)])
        prompts=[]
        def answer(prompt):prompts.append(prompt);return next(answers)
        with patch('builtins.input',side_effect=answer),patch.object(m.pwd,'getpwuid',return_value=types.SimpleNamespace(pw_name='helper')):p=m.prompt_profile()
        self.assertFalse(any('enable one-click' in prompt for prompt in prompts))
        self.assertTrue(p['helper']['quick_approval']);self.assertEqual(p['helper']['id'],'mom')
        self.assertIn('identity_file',p['admin']);self.assertTrue(p['approval_scope']['menus'])
    def test_mom_can_be_the_only_helper(self):
        p=profile();old=p.pop('dad');p.pop('mom');p['helper']=dict(old,kind='mom',label='Mom');p['other_parent']={'enabled':False}
        m.validate(p)
        with patch.object(m.pwd,'getpwnam',return_value=types.SimpleNamespace(pw_dir='/home/learner')):files=m.learner_files(p,12345,key(5),key(4))
        cfg=json.loads(files['/etc/family-help/child.json'][0]);self.assertEqual(cfg['helper_label'],'Mom');self.assertEqual(cfg['helper_slug'],'mom')
        self.assertIn('/usr/local/bin/ask-mom',files);self.assertIn('/usr/local/bin/ask-parent',files);self.assertNotIn('/usr/local/bin/ask-dad',files)
        qml=files['/usr/local/share/family-help/ask-dad/AskDad.qml'][0];self.assertIn(b'"Ask Mom"',qml);self.assertNotIn(b'"Ask Dad"',qml)
        self.assertIn(b'Name=Ask Mom',files['/usr/local/share/applications/org.familylab.Help.desktop'][0])
        helper=m.helper_files(p,pathlib.Path('/home/helper'),pathlib.Path('/home/helper/admin'),pathlib.Path('/home/helper/roles'))
        self.assertEqual(json.loads(helper['.config/family-help/helper.json'][0])['helper_label'],'Mom')
        self.assertNotIn('.config/family-help/dad.json',helper)
        self.assertEqual(json.loads(files['/etc/family-help/teaching.json'][0])['admin'],'parent')
    def test_interactive_mom_profile_needs_no_dad(self):
        answers=iter(['mom','','technical','','','learner','','192.0.2.10','','parent','/not-read/admin-key','','192.0.2.20','','','',m.fingerprint(key(4))])
        prompts=[]
        def answer(prompt):prompts.append(prompt);return next(answers)
        with patch('builtins.input',side_effect=answer),patch.object(m.pwd,'getpwuid',return_value=types.SimpleNamespace(pw_name='helper')):p=m.prompt_profile()
        self.assertEqual(p['helper']['kind'],'mom');self.assertEqual(p['helper']['label'],'Mom');self.assertNotIn('dad',p)
        self.assertFalse(any('Dad desktop' in prompt or 'Dad device' in prompt for prompt in prompts))
    def test_guardian_label_is_escaped_in_qml(self):
        p=profile();p.pop('dad');p.pop('mom');p['helper']={'login':'helper','host':'192.0.2.20','kind':'parent','label':'Aunt "Lee"'}
        m.validate(p)
        with patch.object(m.pwd,'getpwnam',return_value=types.SimpleNamespace(pw_dir='/home/learner')):files=m.learner_files(p,12345,key(5),key(4))
        self.assertIn(json.dumps('Ask Aunt "Lee"').encode(),files['/usr/local/share/family-help/ask-dad/AskDad.qml'][0])
    def test_file_idempotence_drift_and_rollback(self):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder);state=root/'private/state.json'
            tx=m.Files(root,state,staged=True);tx.write('/usr/local/example',b'first');tx.commit()
            original=state.read_bytes();target=root/'usr/local/example';before=target.stat().st_mtime_ns
            again=m.Files(root,state,staged=True);again.write('/usr/local/example',b'first');again.commit()
            self.assertEqual(again.changes,[]);self.assertEqual(state.read_bytes(),original);self.assertEqual(target.stat().st_mtime_ns,before)
            target.write_bytes(b'local edit')
            with self.assertRaises(ValueError):m.Files(root,state,staged=True).write('/usr/local/example',b'update')
            adopt=m.Files(root,state,adopt=True,staged=True);adopt.write('/usr/local/example',b'update');adopt.write('/new',b'new');adopt.rollback()
            self.assertEqual(target.read_bytes(),b'local edit');self.assertFalse((root/'new').exists())
            record=json.loads((adopt.backup/'changes.json').read_text());self.assertEqual(base64.b64decode(record[0]['content']),b'local edit')
    def test_managed_payload_modes_and_no_secrets(self):
        p=profile();account=types.SimpleNamespace(pw_dir='/home/learner')
        with patch.object(m.pwd,'getpwnam',return_value=account):files=m.learner_files(p,12345,key(5),key(4))
        self.assertIn('/usr/local/sbin/family-migrate-child',files)
        self.assertEqual(files['/etc/family-help/teaching.json'][1],0o644)
        self.assertNotIn('identity_file',files['/etc/family-help/teaching.json'][0].decode())
        self.assertIn(b'ForceCommand /usr/local/libexec/family-admin-demo view',files['/etc/ssh/sshd_config.d/40-family-help-viewer.conf'][0])
        self.assertFalse(any('sudoers' in name or '/pam.d/' in name or '/usr/share/omarchy/' in name for name in files))
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder);tx=m.Files(root,root/'private/state.json',staged=True)
            for name,(data,mode,link) in files.items():tx.write(name,data,mode,link)
            tx.commit();again=m.Files(root,root/'private/state.json',staged=True)
            for name,(data,mode,link) in files.items():again.write(name,data,mode,link)
            self.assertFalse(again.changes)
    def test_host_pin_refuses_replacement(self):
        p=profile()
        with patch.object(m,'run',return_value=types.SimpleNamespace(stdout='192.0.2.10 '+key(4)+'\n')):self.assertEqual(m.pinned_host(p),key(4))
        with patch.object(m,'run',return_value=types.SimpleNamespace(stdout='192.0.2.10 '+key(6)+'\n')):
            with self.assertRaises(ValueError):m.pinned_host(p)
    def test_effective_viewer_policy_fails_closed(self):
        with patch.object(m,'run',return_value=types.SimpleNamespace(stdout='forcecommand none\npasswordauthentication yes\n')):
            with self.assertRaises(ValueError):m.verify_viewer_policy()
    def test_helper_config_separates_credentials(self):
        files=m.helper_files(profile(),pathlib.Path('/home/helper'),pathlib.Path('/home/helper/.ssh/admin'),pathlib.Path('/home/helper/.ssh/roles'))
        config=files['.config/family-help/ssh.conf'][0].decode()
        self.assertEqual(config.count('IdentityAgent none'),3)
        self.assertEqual(config.count('ForwardAgent no'),4)
        self.assertEqual(config.count('StrictHostKeyChecking yes'),4)
        self.assertEqual(config.count('BatchMode no'),1)
        self.assertEqual(files['.config/family-help/ssh.conf'][1],0o600)
        self.assertNotIn(b'PRIVATE KEY',b''.join(item[0] for item in files.values() if isinstance(item[0],bytes)))
        for value in ('bad\nHost *','%h','bad\x00path'):
            with self.assertRaises(ValueError):m.ssh_value(value)
    def test_unknown_installers_downgrade(self):
        with patch.object(m.pathlib.Path,'is_file',return_value=False):catalog,changed=m.downgrade_catalog()
        self.assertTrue(changed)
        self.assertTrue(all(catalog[name]['mode']=='manual' for name in changed))
    def test_bundle_excludes_credentials_and_git(self):
        with tempfile.TemporaryDirectory() as folder:
            target=pathlib.Path(folder)/'bundle'
            # Exercise bundle contents independently of the production /tmp prohibition.
            with patch.object(m,'private_path',side_effect=lambda value:pathlib.Path(value)),patch.object(m,'private_write',side_effect=lambda path,data:path.write_bytes(data)):
                m.enrollment_bundle(profile(),str(target))
                result=json.loads((target/'enrollment.json').read_text())
                self.assertNotIn('identity_file',result['admin']);self.assertEqual(result['public_keys'],profile()['public_keys'])
                self.assertFalse((target/'.git').exists());self.assertTrue((target/'master-installation.sh').is_file())
                self.assertFalse(any(b'BEGIN OPENSSH PRIVATE KEY' in path.read_bytes() for path in target.rglob('*') if path.is_file() and path.name!='family_install.py'))
                with self.assertRaises(ValueError):m.enrollment_bundle(profile(),str(target))
    def test_admin_key_encryption_requirement(self):
        with tempfile.TemporaryDirectory() as folder:
            for name,passphrase in [('unencrypted',''),('encrypted','synthetic-test-only')]:
                path=pathlib.Path(folder)/name
                subprocess.run(['/usr/bin/ssh-keygen','-q','-t','ed25519','-N',passphrase,'-f',str(path)],check=True)
                with patch.object(m,'private_path',side_effect=lambda value:pathlib.Path(value)):
                    if passphrase:self.assertEqual(m.check_admin_identity(str(path)),path)
                    else:
                        with self.assertRaises(ValueError):m.check_admin_identity(str(path))
    def test_nondefault_port_includes_loopback_viewer(self):
        p=profile();p['learner']['port']=2222
        with patch.object(m.pwd,'getpwnam',return_value=types.SimpleNamespace(pw_dir='/home/learner')):files=m.learner_files(p,12345,key(5),key(4))
        self.assertTrue(files['/etc/family-help/localhost_known_hosts'][0].startswith(b'[127.0.0.1]:2222 '))
        self.assertEqual(json.loads(files['/etc/family-help/child.json'][0])['port'],2222)
    def test_real_ssh_config_parser_without_network(self):
        with tempfile.TemporaryDirectory() as folder:
            home=pathlib.Path(folder);files=m.helper_files(profile(),home,home/'admin',home/'roles')
            config=home/'ssh.conf';config.write_bytes(files['.config/family-help/ssh.conf'][0])
            for role in ('poll','view','control','admin'):
                value=subprocess.check_output(['/usr/bin/ssh','-G','-F',str(config),'family-learner-a-'+role],text=True,stderr=subprocess.DEVNULL)
                fields=dict(line.split(' ',1) for line in value.splitlines() if ' ' in line)
                self.assertEqual(fields['hostname'],'192.0.2.10');self.assertEqual(fields['forwardagent'],'no')
                self.assertEqual(fields['user'],'parent' if role=='admin' else 'learner')
                self.assertEqual(fields['batchmode'],'no' if role=='admin' else 'yes')
    def test_learner_orchestration_with_no_live_actions(self):
        child=types.SimpleNamespace(pw_uid=12345,pw_gid=12345,pw_name='learner',pw_dir='/home/learner')
        admin=types.SimpleNamespace(pw_uid=12346,pw_gid=12346,pw_name='parent',pw_dir='/home/parent')
        viewer=types.SimpleNamespace(pw_uid=960,pw_gid=960,pw_name='familyviewer',pw_dir='/var/lib/family-help-viewer')
        accounts={'learner':child,'parent':admin,'familyviewer':viewer};phases=[];commands=[]
        class Tx:
            changes=[]
            def __init__(self,*a):self.files={}
            def write(self,name,*args):self.files[name]=args
            def commit(self):pass
            def rollback(self):raise AssertionError('Unexpected rollback')
        def invoke(command,**kwargs):
            commands.append(command)
            return types.SimpleNamespace(returncode=0,stdout='familyviewer L 1 0 99999 7 -1' if 'passwd' in command[0] else '',stderr='')
        def as_child(account,payload):
            self.assertEqual(account.pw_uid,12345);phases.append(payload['phase'])
            return types.SimpleNamespace(stdout=json.dumps({'public_key':key(5)}) if payload['phase']=='viewer-key' else '')
        original_read=m.pathlib.Path.read_text
        def read(path,*args,**kwargs):
            if str(path)=='/etc/ssh/ssh_host_ed25519_key.pub':return key(4)
            return original_read(path,*args,**kwargs)
        with patch.object(m.os,'geteuid',return_value=0),patch.dict(os.environ,{'SUDO_USER':'parent'}),patch.object(m.pwd,'getpwnam',side_effect=accounts.__getitem__),patch.object(m,'groups',side_effect=lambda user:{'wheel'} if user.pw_name=='parent' else {user.pw_name}),patch.object(m.shutil,'which',return_value='/mock/tool'),patch.object(m.subprocess,'run',side_effect=invoke),patch.object(m,'ensure_directory'),patch.object(m,'as_learner',side_effect=as_child),patch.object(m.pathlib.Path,'read_text',read),patch.object(m,'downgrade_catalog',return_value=({},[])),patch.object(m,'Files',Tx),patch.object(m,'verify_viewer_policy'):
            m.apply_learner(profile(),types.SimpleNamespace(adopt_existing=False,activate=True))
        self.assertEqual(phases,['viewer-key','learner-config','menu','activate'])
        self.assertFalse(any(command[0].endswith(('usermod','pacman','reboot')) for command in commands))
    def test_child_menu_and_keys_are_idempotent(self):
        source=(ROOT/'setup/user_setup.py').read_text().replace('/usr/local/libexec/family-menu-catalog.json',str(ROOT/'assistance/family-menu-catalog.json'))
        with tempfile.TemporaryDirectory() as folder:
            home=pathlib.Path(folder);menu=home/'.config/omarchy/extensions/omarchy-menu.jsonc';menu.parent.mkdir(parents=True)
            menu.write_text('{"personal.example":{"label":"Keep","action":"true"}}')
            def run(payload):
                code="import os; os.geteuid=lambda:12345\n"+source.replace("if __name__=='__main__':main(json.loads(sys.argv[1]))",'')+'\nmain('+repr(payload)+')\n'
                subprocess.run(['/usr/bin/python3','-c',code],env=dict(os.environ,HOME=folder),check=True,capture_output=True)
            run({'phase':'menu'});first=menu.read_bytes();run({'phase':'menu'});self.assertEqual(menu.read_bytes(),first)
            self.assertEqual(json.loads(first)['personal.example']['action'],'true')
            payload={'phase':'learner-config','source_ip':'192.0.2.20','public_keys':profile()['public_keys']}
            run(payload);self.assertTrue((home/'.local/share/family-lab').is_dir());keys=home/'.ssh/authorized_keys';first=keys.read_bytes();run(payload);self.assertEqual(keys.read_bytes(),first)
            self.assertEqual(first.count(b'command='),3);self.assertIn(b'restrict,pty,command=',first)
            self.assertNotIn(b'restrict,pty,command="/usr/local/libexec/family-help-child poll"',first)
            keys.write_text(key(1)+'\n'+first.decode())
            with self.assertRaises(subprocess.CalledProcessError):run(payload)
if __name__=='__main__':unittest.main()
