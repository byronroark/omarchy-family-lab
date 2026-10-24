"""No real service or filter changes: synthetic enrollment, commands and responses."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


collection=load('collection','integrations/family_collection_control.py')
panel=load('integrations','assistance/family_integrations.py')


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.config={'provider':'activitywatch','allow_collection_control':True}
        self.active=False;self.calls=[];self.loaded=True;self.service_active=None
    def command(self,args,**kwargs):
        self.calls.append(args)
        if 'start' in args:self.active=True
        if 'stop' in args:self.active=False
        if 'show' in args:
            active='active' if self.active else 'inactive'
            if collection.UNIT in args:
                output='LoadState='+('loaded' if self.loaded else 'not-found')+'\nActiveState='+active+'\nWants='+' '.join(collection.SERVICES)+'\n'
            else:
                output='LoadState=loaded\nActiveState='+(self.service_active or active)+'\nPartOf='+collection.UNIT+'\n'
        else:output=''
        return types.SimpleNamespace(stdout=output,returncode=0)
    def test_optin_fixed_target_and_confirmed_start_stop(self):
        for enabled in (True,False):
            result=collection.control(self.config,{'op':'collection-set','enabled':enabled,'acknowledge_raw_storage':enabled},self.command)
            self.assertEqual(result['enabled'],enabled)
        for args in self.calls:
            self.assertEqual(args[:2],['/usr/bin/systemctl','--user'])
            self.assertNotIn('sudo',args);self.assertNotIn('enable',args)
    def test_ordinary_report_role_cannot_start_collection(self):
        for config,op in [({'provider':'activitywatch'},{'op':'collection-status'}),
                          (self.config,{'op':'collection-set','enabled':True,'acknowledge_raw_storage':False}),
                          (self.config,{'op':'collection-set','enabled':True,'acknowledge_raw_storage':True,'unit':'arbitrary'}),
                          (self.config,{'op':'sudo'})]:
            with self.assertRaises(ValueError):collection.control(config,op,self.command)
        self.assertFalse(self.calls)
    def test_missing_target_and_failed_watcher_are_not_active(self):
        self.loaded=False
        self.assertFalse(collection.control(self.config,{'op':'collection-status'},self.command)['ready'])
        self.loaded=True;self.active=True;self.service_active='failed'
        result=collection.control(self.config,{'op':'collection-status'},self.command)
        self.assertFalse(result['enabled']);self.assertEqual(result['state'],'incomplete')


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        self.path=self.home/'.config/family-lab/adguard-control.json';self.path.parent.mkdir(parents=True)
        self.enrollment={'url':'https://filter.example.org','username':'parent','password':'SYNTHETIC',
                         'peer':'child','client_name':'Child device','client_ids':['192.0.2.40']}
        self.write()
        self.row={'name':'Child device','ids':['192.0.2.40'],'use_global_settings':False,
                  'filtering_enabled':False,'parental_enabled':False,'safebrowsing_enabled':False,
                  'blocked_services':['example-service'],'safe_search':{'enabled':True},'ignore_querylog':True}
        self.other={'name':'Adult device','ids':['192.0.2.41']}
        self.calls=[];self.global_enabled=True;self.accept=True
    def write(self):
        self.path.write_text(json.dumps(self.enrollment));self.path.chmod(0o600)
    def api(self,endpoint,data=None):
        self.calls.append((endpoint,copy.deepcopy(data)))
        if endpoint=='clients':return {'clients':[copy.deepcopy(self.row),copy.deepcopy(self.other)]}
        if endpoint=='status':return {'protection_enabled':self.global_enabled,'running':True}
        if endpoint=='clients/update':
            if self.accept:self.row=copy.deepcopy(data['data'])
            return {}
        raise AssertionError('Unexpected endpoint')
    def controller(self):
        value=panel.AdGuard('child',self.home);value.api=self.api;return value
    def test_only_enrolled_child_protections_change_and_are_confirmed(self):
        original_other=copy.deepcopy(self.other)
        for enabled in (True,False):
            result=self.controller().set_enabled(enabled)
            self.assertEqual(result['client_enabled'],enabled)
        self.assertEqual(self.other,original_other)
        self.assertEqual(self.row['safe_search'],{'enabled':True})
        self.assertTrue(self.row['ignore_querylog'])
        self.assertEqual(self.row['blocked_services'],['example-service'])
        self.assertTrue(all(endpoint in ('clients','status','clients/update') for endpoint,_ in self.calls))
    def test_global_pause_identity_change_and_inheritance_fail_before_update(self):
        for change in ('global','identity','inheritance'):
            self.global_enabled=True;self.row['ids']=['192.0.2.40'];self.row['use_global_settings']=False;self.calls=[]
            if change=='global':self.global_enabled=False
            elif change=='identity':self.row['ids']=['192.0.2.99']
            else:self.row['use_global_settings']=True
            with self.assertRaises(ValueError):self.controller().set_enabled(True)
            self.assertNotIn('clients/update',[endpoint for endpoint,_ in self.calls])
    def test_refused_change_never_reports_success(self):
        self.accept=False
        with self.assertRaisesRegex(ValueError,'did not confirm'):self.controller().set_enabled(True)
    def test_private_enrollment_https_and_device_scope(self):
        self.path.chmod(0o644)
        with self.assertRaises(ValueError):self.controller()
        for key,value in [('url','http://filter.example.org'),('url','https://user:pass@filter.example.org'),
                          ('client_ids',['192.0.2.0/24']),('client_ids',['*']),('peer','another-child')]:
            original=copy.deepcopy(self.enrollment);self.enrollment[key]=value;self.write()
            with self.assertRaises(ValueError):self.controller()
            self.enrollment=original
        self.write();self.path.unlink();self.path.symlink_to('/dev/null')
        with self.assertRaises(OSError):self.controller()


if __name__=='__main__':unittest.main()
