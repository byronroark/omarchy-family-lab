"""Additional controls parent enrollment changes only parent credentials/routing."""
import copy,json,pathlib,types,unittest
from unittest.mock import Mock,patch
from check_enrollment import m,key
from check_tutor_enrollment import parent_profile

ROOT=pathlib.Path(__file__).resolve().parents[1]

class ParentEnrollment(unittest.TestCase):
    def test_add_parent_preserves_enforcement_and_only_reloads_parent_registry(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            stage=pathlib.Path(folder)
            def mapped(value):
                value=str(value)
                return stage/value.lstrip('/') if value.startswith(('/etc/','/var/lib/')) else pathlib.Path(value)
            source=(ROOT/'setup/policy_setup.py').read_text().replace('import grp,hashlib,json,os,pathlib,pwd,subprocess','import grp,hashlib,json,os,pwd,subprocess\npathlib=staged_pathlib')
            scope={'staged_pathlib':types.SimpleNamespace(Path=mapped)};exec(compile(source,'<parent-enrollment>','exec'),scope)
            p=parent_profile();p['policy_public_key']=key(9)
            original={'subjects':{'learner-a':{'uid':2101,'login':'learner'}},'parents':{'958':'Dad'},'guards':{'959':'learner-a'},'browsers':[],'parent_helpers':{'dad':958}}
            path=mapped('/etc/family-lab/enrollment.json');path.parent.mkdir(parents=True);path.write_text(json.dumps(original))
            policy=mapped('/var/lib/family-lab/policy.json');policy.parent.mkdir(parents=True);policy.write_text('ENFORCED POLICY UNCHANGED')
            scope['account']=lambda *args:types.SimpleNamespace(pw_name='flpolicy-mom',pw_uid=960)
            requests=[]
            scope['parent_request']=lambda req: requests.append(req) or ({'capabilities':{'parent_enrollment_reload':True}} if req['op']=='get' else {'reloaded':True})
            writes=[]
            class Files(m.Files):
                def write(self,name,*args,**kwargs):writes.append(name);return super().write(name,*args,**kwargs)
            commands=[]
            def run(command,**kwargs):
                commands.append(command)
                return types.SimpleNamespace(stdout='forcecommand /usr/local/libexec/family-lab-policy remote\ndisableforwarding yes\npasswordauthentication no\n')
            api={'selected_helper':m.selected_helper,'plain':m.plain,'public_key':m.public_key,'encoded':m.encoded,'trusted_system_file':lambda path:None,'ensure_directory':lambda path,mode:mapped(path).mkdir(parents=True,exist_ok=True),'Files':lambda base,state,adopt:Files(stage,mapped(state),adopt,staged=True),'run':run}
            accounts={'learner':types.SimpleNamespace(pw_uid=2101),'parent':types.SimpleNamespace(pw_uid=2102)}
            with patch.object(scope['os'],'geteuid',return_value=0),patch.object(scope['pwd'],'getpwnam',side_effect=accounts.__getitem__):
                scope['install_parent'](api,p,types.SimpleNamespace())
            merged=json.loads(path.read_text())
            self.assertEqual(merged['parents'],{'958':'Dad','960':'Mom'})
            self.assertEqual(merged['parent_helpers'],{'dad':958,'mom':960})
            for name in ['subjects','guards','browsers']:self.assertEqual(merged[name],original[name])
            self.assertEqual(policy.read_text(),'ENFORCED POLICY UNCHANGED')
            self.assertEqual(requests,[{'op':'get'},{'op':'reload-parents'}])
            self.assertEqual(set(writes),{'/etc/family-lab/enrollment.json','/etc/family-lab/parents/mom.keys','/etc/ssh/sshd_config.d/42-family-policy-mom.conf'})
            self.assertNotIn(['/usr/bin/systemctl','restart','family-lab-policy.service'],commands)

if __name__=='__main__':unittest.main()
