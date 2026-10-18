"""Stage the complete controls installer; intercept every privileged operation."""
import hashlib,json,os,pathlib,types,unittest
from unittest.mock import patch
import tempfile
from check_enrollment import m as api_module,profile,key
ROOT=pathlib.Path(__file__).resolve().parents[1]
class SetupTests(unittest.TestCase):
    def test_root_files_disabled_defaults_identity_separation_and_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            stage=pathlib.Path(directory)
            def mapped(value):
                text=os.fspath(value)
                return stage/text.lstrip('/') if text.startswith(('/etc/','/var/lib/','/usr/local/','/run/family-lab/')) else pathlib.Path(value)
            (stage/'etc/pam.d').mkdir(parents=True)
            for name in ('system-login','omarchy-lock-password','omarchy-lock-fingerprint'):(stage/'etc/pam.d'/name).write_text('auth include system-auth\naccount include system-auth\n')
            source=(ROOT/'setup/policy_setup.py').read_text().replace('import grp,hashlib,json,os,pathlib,pwd,subprocess','import grp,hashlib,json,os,pwd,subprocess\npathlib=staged_pathlib')
            namespace={'staged_pathlib':types.SimpleNamespace(Path=mapped)};exec(compile(source,'<staged controls>','exec'),namespace)
            p=profile();p.pop('dad');p.pop('mom');p['helper']={'id':'dad','kind':'dad','label':'Dad','login':'helper','host':'192.0.2.20','capability':'technical'};p['policy_public_key']=key(9);p['controls_timezone']='America/New_York'
            guard='flguard-'+hashlib.sha256(p['learner']['id'].encode()).hexdigest()[:12]
            accounts={'learner':types.SimpleNamespace(pw_name='learner',pw_uid=2101,pw_gid=2101),'parent':types.SimpleNamespace(pw_name='parent',pw_uid=2102,pw_gid=2102),'flpolicy-dad':types.SimpleNamespace(pw_name='flpolicy-dad',pw_uid=958,pw_gid=958,pw_dir='/var/lib/family-policy/dad'),guard:types.SimpleNamespace(pw_name=guard,pw_uid=959,pw_gid=959,pw_dir='/var/lib/family-guards/learner-a')}
            commands=[];checks=[]
            def run(command,**kwargs):
                commands.append(command)
                if command[:2]==['/usr/bin/passwd','-S']:return types.SimpleNamespace(stdout=command[-1]+' L 1 0 99999 7 -1',returncode=0)
                if command[:2]==['/usr/bin/sshd','-T']:
                    fields={'ForceCommand':'/usr/local/libexec/family-lab-policy remote','AuthorizedKeysFile':'/etc/family-lab/policy-dad.keys','PermitTTY':'no','DisableForwarding':'yes','PermitUserRC':'no','PermitUserEnvironment':'no','PasswordAuthentication':'no','KbdInteractiveAuthentication':'no','AuthenticationMethods':'publickey','AuthorizedKeysCommand':'none'}
                    return types.SimpleNamespace(stdout='\n'.join(key+' '+value for key,value in fields.items()),returncode=0)
                return types.SimpleNamespace(stdout='',returncode=0)
            class Files(api_module.Files):
                def __init__(self,base,state,adopt=False):super().__init__(stage,mapped(state),adopt,staged=True)
                def write(self,name,*args,**kwargs):
                    if str(name).startswith(str(stage)):name='/'+str(pathlib.Path(name).relative_to(stage))
                    return super().write(name,*args,**kwargs)
            api=dict(vars(api_module),run=run,ensure_directory=lambda path,mode:mapped(path).mkdir(parents=True,exist_ok=True),check_sudo_absent=lambda account:checks.append(account.pw_name),trusted_system_file=lambda _:None,groups=lambda account:{account.pw_name}|({'family-lab-parents'} if account.pw_name=='flpolicy-dad' else set()),Files=Files)
            args=types.SimpleNamespace(adopt_existing=True,activate=False,enable_pam=True)
            with patch.object(os,'geteuid',return_value=0),patch.dict(os.environ,{'SUDO_USER':'parent'}),patch('pwd.getpwnam',side_effect=accounts.__getitem__),patch('grp.getgrnam',return_value=types.SimpleNamespace(gr_gid=957)),patch('subprocess.run',return_value=types.SimpleNamespace(returncode=1)):
                namespace['install'](api,p,args)
                before={str(path.relative_to(stage)):path.read_bytes() for path in stage.rglob('*') if path.is_file()}
                namespace['install'](api,p,args)
                after={str(path.relative_to(stage)):path.read_bytes() for path in stage.rglob('*') if path.is_file()}
            self.assertEqual(before,after)
            policy=json.loads((stage/'var/lib/family-lab/policy.json').read_text())['policy']
            self.assertEqual(policy['timezone'],'America/New_York');item=policy['subjects']['learner-a']
            self.assertEqual(item['mode'],'off');self.assertEqual(item['breaks'],{'enabled':True,'use_minutes':60,'break_minutes':15})
            self.assertFalse((stage/'etc/family-lab/guard-ready').exists())
            registry=json.loads((stage/'etc/family-lab/enrollment.json').read_text())
            self.assertEqual(registry['parents'],{'958':'Dad'});self.assertEqual(registry['guards'],{'959':'learner-a'});self.assertEqual(registry['parent_helpers'],{'dad':958})
            self.assertIn('learner',checks);self.assertIn('flpolicy-dad',checks);self.assertIn(guard,checks)
            self.assertEqual((stage/'etc/pam.d/omarchy-lock-password').read_text().count('unlock-check'),1)
            self.assertTrue((stage/'usr/local/share/family-lab/guard/Dino/BreakCard.qml').exists())
            self.assertFalse(any('sudoers' in path for path in after))
            self.assertFalse(any(command[0].endswith(('reboot','pacman','loginctl')) for command in commands))
            self.assertFalse(any('start' in command or 'enable' in command for command in commands))
if __name__=='__main__':unittest.main()
