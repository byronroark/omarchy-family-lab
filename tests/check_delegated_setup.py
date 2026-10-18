"""Simulated root enrollment: intercept every account/service/file mutation."""
import importlib.util,json,os,pathlib,shutil,subprocess,tempfile,types,unittest
from unittest.mock import patch
from check_enrollment import profile,key,m as enroll
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('approval_setup_test',ROOT/'setup/approval_setup.py');setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
class Enrollment(unittest.TestCase):
    def test_add_parent_preserves_existing_technical_configuration(self,technical=False):
        p=profile();p.pop('dad');p.pop('mom');p['admin'].pop('identity_file');p['helper']={'id':'mom','kind':'mom','label':'Mom','login':'helper','host':'192.0.2.20','capability':'approver'};p['approval_scope']={'menus':[],'packages':['extra/jq']};p['public_keys']={'approval':key(9)}
        if technical:
            p['helper'].update(capability='technical',quick_approval=True);p['admin']['identity_file']='/not-used/admin'
            p['public_keys'].update({role:key(i) for i,role in enumerate(('poll','view','control'),1)})
        accounts={name:types.SimpleNamespace(pw_name=name,pw_uid=uid,pw_gid=uid,pw_dir=home) for name,uid,home in [('learner',1000,'/home/learner'),('parent',1001,'/home/parent'),('familyviewer',960,'/var/lib/family-help-viewer'),('familyap-mom',959,'/var/lib/family-approvers/mom')]}
        commands=[];writes=[];sudo_checked=[];policy_checked=[]
        class Tx:
            changes=[]
            def __init__(self,*args):pass
            def write(self,name,*args):writes.append(name)
            def commit(self):commands.append(['COMMIT'])
            def rollback(self):commands.append(['ROLLBACK'])
        def run(args,**kwargs):commands.append(args);return types.SimpleNamespace(stdout='familyap-mom L 1 0 99999 7 -1',returncode=0)
        api=dict(vars(enroll),run=run,Files=Tx,ensure_directory=lambda *args:None,trusted_system_file=lambda *args:None,check_sudo_absent=lambda account:sudo_checked.append(account.pw_name),groups=lambda account:{account.pw_name,'family-help-approvers'} if account.pw_name=='familyap-mom' else {account.pw_name})
        original_read=pathlib.Path.read_bytes;original_text=pathlib.Path.read_text;original_exists=pathlib.Path.exists
        def read(path):
            if str(path).startswith('/usr/local/libexec/'):return (ROOT/'assistance'/path.name).read_bytes()
            return original_read(path)
        def text(path,*args,**kwargs):
            if str(path)=='/etc/family-help/teaching.json':return json.dumps({'child':'learner','admin':'parent','viewer':'familyviewer'})
            return original_text(path,*args,**kwargs)
        def exists(path):return False if str(path)=='/etc/family-help/approvers.json' else original_exists(path)
        with patch.object(setup.os,'geteuid',return_value=0),patch.dict(os.environ,{'SUDO_USER':'parent'}),patch.object(setup.pwd,'getpwnam',side_effect=accounts.__getitem__),patch.object(setup.grp,'getgrnam',return_value=types.SimpleNamespace(gr_gid=958)),patch.object(setup.pathlib.Path,'read_bytes',read),patch.object(setup.pathlib.Path,'read_text',text),patch.object(setup.pathlib.Path,'exists',exists),patch.object(setup.subprocess,'run',return_value=types.SimpleNamespace(returncode=1)),patch.object(setup,'verify_policy',side_effect=lambda *args:policy_checked.append(args[1:])):
            setup.install(api,p,types.SimpleNamespace(adopt_existing=False))
        self.assertEqual(sudo_checked,['learner','familyap-mom']);self.assertEqual(policy_checked,[('familyap-mom','mom')]);self.assertIn(['COMMIT'],commands)
        self.assertFalse(any(name.endswith(('child.json','teaching.json','family-help-child')) or '/home/' in name or 'sudoers' in name for name in writes))
        self.assertFalse(any(command[0].endswith(('usermod','pacman','reboot')) for command in commands))
        self.assertIn(['/usr/bin/systemctl','enable','--now','family-help-approval.socket'],commands)
    def test_add_technical_quick_approval_preserves_existing_configuration(self):
        self.test_add_parent_preserves_existing_technical_configuration(technical=True)
    @unittest.skipUnless(shutil.which('sshd'),'OpenSSH server parser unavailable')
    def test_generated_ssh_rule_with_real_parser(self):
        p=profile();p.pop('dad');p.pop('mom');p['admin'].pop('identity_file')
        p['helper']={'id':'mom','kind':'mom','label':'Mom','login':'helper','host':'192.0.2.20','capability':'approver'}
        p['approval_scope']={'packages':[],'menus':[]};p['public_keys']={'approval':key(9)}
        files=setup.desired_files(vars(enroll),p,959,{'version':1,'principals':{}})
        rule=files['/etc/ssh/sshd_config.d/41-family-help-mom.conf'][0].decode()
        with tempfile.TemporaryDirectory() as directory:
            home=pathlib.Path(directory);host=home/'hostkey';config=home/'sshd.conf'
            subprocess.run(['/usr/bin/ssh-keygen','-q','-t','ed25519','-N','','-f',str(host)],check=True)
            config.write_text('HostKey '+str(host)+'\nPermitUserEnvironment no\n'+rule)
            result=subprocess.run([shutil.which('sshd'),'-t','-f',str(config)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([shutil.which('sshd'),'-T','-f',str(config),'-C','user=familyap-mom,host=localhost,addr=192.0.2.20'],capture_output=True,text=True,check=True)
            setup.verify_policy({'run':lambda *args,**kwargs:result},'familyap-mom','mom')
            config.write_text('HostKey '+str(host)+'\nPermitUserEnvironment yes\n'+rule)
            result=subprocess.run([shutil.which('sshd'),'-T','-f',str(config),'-C','user=familyap-mom,host=localhost,addr=192.0.2.20'],capture_output=True,text=True,check=True)
            with self.assertRaises(ValueError):setup.verify_policy({'run':lambda *args,**kwargs:result},'familyap-mom','mom')
    def test_effective_policy_must_match(self):
        api={'run':lambda *args,**kwargs:types.SimpleNamespace(stdout='forcecommand none\npermittty yes\n')}
        with self.assertRaises(ValueError):setup.verify_policy(api,'familyap-mom','mom')
if __name__=='__main__':unittest.main()
