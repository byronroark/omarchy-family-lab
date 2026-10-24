"""Parent enrollment checks: no Docker, network, accounts or system writes."""
import copy
import importlib.util
import json
from pathlib import Path
import types
import unittest
from unittest.mock import Mock,patch
from check_enrollment import m,profile,key

spec=importlib.util.spec_from_file_location('tutor',Path(__file__).resolve().parents[1]/'setup/tutor_setup.py')
tutor=importlib.util.module_from_spec(spec);spec.loader.exec_module(tutor)

def parent_profile():
    p=profile();p.pop('dad');p.pop('mom');p['admin'].pop('identity_file')
    p['learner']['host']='192.168.50.10'
    p['helper']={'kind':'mom','label':'Mom','id':'mom','login':'helper','host':'192.168.50.20','capability':'approver'}
    p['approval_scope']={'packages':[],'menus':[]};p['public_keys']={'approval':key(8)}
    p['tutor']={'enabled':True,'port':3785,'parent_login':'mom','firewall':True};p['enroll_controls']=True
    return p

class TutorEnrollment(unittest.TestCase):
    def test_fresh_mom_wizard_combines_approver_controls_and_tutoring(self):
        answers=iter(['mom','','approver','','','learner','','192.168.50.10','','parent','','192.168.50.20','','','','SHA256:'+('A'*43),'yes','yes','mom'])
        prompts=[]
        def answer(prompt):prompts.append(prompt);return next(answers)
        with patch('builtins.input',side_effect=answer),patch.object(m.pwd,'getpwuid',return_value=types.SimpleNamespace(pw_name='helper')):
            p=m.prompt_profile()
        self.assertEqual(m.capability(p),'approver');self.assertTrue(p['enroll_controls'])
        self.assertTrue(p['tutor']['enabled']);self.assertEqual(p['tutor']['parent_login'],'mom')
        self.assertNotIn('identity_file',p['admin'])
        self.assertFalse(any('private key' in prompt.lower() for prompt in prompts))

    def test_approval_only_and_tutor_parent_are_independent(self):
        p=parent_profile();m.validate(p)
        self.assertEqual(m.expected_keys(p),{'approval'})
        files=m.helper_files(p,Path('/home/helper'),None,Path('/home/helper/keys'))
        ssh=files['.config/family-help/ssh.conf'][0].decode()
        self.assertNotIn('User parent\n',ssh);self.assertNotIn('admin-key',ssh)
        self.assertNotIn('providers',json.loads(files['.config/family-help/tutor.json'][0]))
        desktop=files['.local/share/applications/org.familylab.AI.desktop'][0].decode()
        self.assertIn('http://192.168.50.10:3785/settings/connections',desktop)
        self.assertIn('.local/share/applications/org.familylab.Onboarding.desktop',files)

    def test_disabled_profile_is_backward_compatible(self):
        self.assertEqual(tutor.helper_files(profile()),{})
        m.validate(profile())

    def test_rejects_arbitrary_addresses_ports_roles_and_invalid_flags(self):
        for field,value in [('port',True),('port',8080),('parent_login','learner'),('parent_login','mom;sh'),('enabled','yes'),('firewall','yes')]:
            p=parent_profile();p['tutor'][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):m.validate(p)
        for host in ['127.0.0.1','0.0.0.0','8.8.8.8','http://192.168.1.5','::1']:
            p=parent_profile();p['learner']['host']=host
            with self.subTest(host=host),self.assertRaises(ValueError):m.validate(p)

    def test_existing_policy_key_survives_helper_reapply(self):
        p=parent_profile();p['policy_public_key']=key(9)
        files=m.helper_files(p,Path('/home/helper'),None,Path('/home/helper/keys'))
        ssh=files['.config/family-help/ssh.conf'][0].decode()
        self.assertEqual(ssh.count('# BEGIN family-policy mom'),1)
        self.assertIn('User flpolicy-mom',ssh)
        self.assertEqual(json.loads(files['.config/family-help/helper.json'][0])['policy_alias'],'family-learner-a-policy-mom')

    def test_host_requires_managed_identity_no_socket_and_exact_origin(self):
        p=parent_profile()
        item={'Config':{'Labels':{'family-learning.owner':'learner-host'},'Env':['FAMILY_LEARNING_ENABLED=1','FAMILY_LEARNING_LOCAL_ONLY=1','FAMILY_LEARNER_HOST=1','FAMILY_PARENT_CLOUD=1','FAMILY_LEARNING_ORIGIN='+tutor.address(p)]},'State':{'Running':True},'HostConfig':{'PortBindings':{}},'Mounts':[{'Destination':'/app/data','Source':'/var/lib/family-learning/data'}]}
        runner=Mock(return_value=types.SimpleNamespace(stdout=json.dumps([item])))
        tutor.inspect_host(p,runner)
        for change in ['socket','origin','running','label','ports']:
            bad=copy.deepcopy(item)
            if change=='socket':bad['Mounts'].append({'Destination':'/var/run/docker.sock','Source':'/var/run/docker.sock'})
            if change=='origin':bad['Config']['Env'][-1]='FAMILY_LEARNING_ORIGIN=http://localhost:3785'
            if change=='running':bad['State']['Running']=False
            if change=='label':bad['Config']['Labels']={}
            if change=='ports':bad['HostConfig']['PortBindings']={'3782/tcp':[{}]}
            runner.return_value.stdout=json.dumps([bad])
            with self.subTest(change=change),self.assertRaises(ValueError):tutor.inspect_host(p,runner)

    def test_existing_learner_is_never_promoted(self):
        p=parent_profile()
        with patch.object(tutor.os,'geteuid',return_value=0),patch.object(tutor,'inspect_host'),patch.object(tutor,'check_reachable'),patch.object(tutor.pwd,'getpwnam',return_value=types.SimpleNamespace(pw_uid=956,pw_gid=954)),patch.object(tutor.subprocess,'check_output',return_value=json.dumps([{'username':'mom','role':'user'}])),patch.object(tutor.subprocess,'run') as execute:
            with self.assertRaisesRegex(ValueError,'no automatic role promotion'):tutor.install({},p,None)
            execute.assert_not_called()

if __name__=='__main__':unittest.main()
