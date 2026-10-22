"""Break scheduling and parent decisions without any installed policy or lock."""
import copy,importlib.util,json,pathlib,tempfile,types,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('breaks',ROOT/'parental/family_breaks.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class BreakTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=pathlib.Path(self.temp.name)/'breaks.json'
        def write(path,value):
            temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value));temporary.replace(path)
        self.write=write;self.engine=m.Breaks(self.path,lambda path:json.loads(path.read_text()),write)
        self.config={'child':{'enabled':True,'use_minutes':60,'break_minutes':15}}
    def due(self):
        for i in range(360):self.engine.tick(self.config,{'child'},10,1000+i*10,'boot',i*10)
        return self.engine.view('child',4600,'boot',3600)
    def test_hour_then_full_protected_break_then_new_hour(self):
        state=self.due();self.assertEqual(state['phase'],'due');self.assertEqual(state['remaining_seconds'],900)
        self.engine.tick(self.config,{'child'},10,10000,'boot',9000)
        self.assertEqual(self.engine.view('child',10000,'boot',9000)['remaining_seconds'],900)
        self.engine.protected('child',state['episode'],10000,'boot',9000)
        self.assertEqual(self.engine.view('child',10100,'boot',9100)['remaining_seconds'],800)
        self.engine.tick(self.config,{'child'},10,10900,'boot',9900)
        self.assertEqual(self.engine.view('child',10900,'boot',9900)['phase'],'use')
        self.assertEqual(self.engine.view('child',10900,'boot',9900)['used_seconds'],0)
        self.engine.tick(self.config,{'child'},10,10910,'boot',9910)
        self.assertEqual(self.engine.view('child',10910,'boot',9910)['used_seconds'],10)
    def test_restart_and_reboot_never_reset_use_or_unprotected_break(self):
        self.engine.tick(self.config,{'child'},10,1000,'boot',0)
        self.engine=m.Breaks(self.path,lambda path:json.loads(path.read_text()),self.write)
        self.assertEqual(self.engine.view('child',2000,'other',0)['used_seconds'],10)
        state=self.due();self.engine.tick(self.config,set(),0,20000,'other',0)
        self.assertEqual(self.engine.view('child',20000,'other',0)['remaining_seconds'],900)
        self.assertEqual(state['episode'],self.engine.view('child',20000,'other',0)['episode'])
    def test_suspend_counts_as_break_but_wall_clock_jump_does_not(self):
        state=self.due();self.engine.protected('child',state['episode'],5000,'boot',4000)
        self.assertEqual(self.engine.view('child',999999,'boot',4001)['remaining_seconds'],899)
        self.assertEqual(self.engine.view('child',1,'boot',4900)['remaining_seconds'],0)
        self.engine.tick(self.config,set(),0,5001,'newboot',1)
        self.assertGreater(self.engine.view('child',5001,'newboot',1)['remaining_seconds'],0)
    def test_skip_shorten_extend_are_episode_bound_and_parent_only(self):
        state=self.due();self.engine.protected('child',state['episode'],4600,'boot',3600)
        req=self.engine.ask('child',2102,state['episode'],0,'shorten',5,4600,'boot',3600)
        self.assertEqual(len(self.engine.pending(2102)),1);self.assertEqual(self.engine.pending(2103),[])
        with self.assertRaises(ValueError):self.engine.decide(2103,req['id'],'approve',4600,'boot',3600)
        result=self.engine.decide(2102,req['id'],'approve',4600,'boot',3600);self.assertEqual(result['status'],'approved')
        self.assertEqual(self.engine.view('child',4600,'boot',3600)['remaining_seconds'],600)
        with self.assertRaises(ValueError):self.engine.decide(2102,req['id'],'approve',4600,'boot',3600)
        req=self.engine.ask('child',2103,state['episode'],1,'extend',5,4600,'boot',3600)
        self.engine.decide(2103,req['id'],'approve',4600,'boot',3600)
        self.assertEqual(self.engine.view('child',4600,'boot',3600)['remaining_seconds'],900)
        req=self.engine.ask('child',2102,state['episode'],2,'skip',0,4600,'boot',3600)
        self.engine.decide(2102,req['id'],'approve',4600,'boot',3600)
        self.assertEqual(self.engine.view('child',4600,'boot',3600)['phase'],'use')
        self.assertEqual(self.engine.view('child',4600,'boot',3600)['used_seconds'],0)
    def test_denial_and_requests_never_change_deadline(self):
        state=self.due();before=copy.deepcopy(self.engine.state['learners'])
        req=self.engine.ask('child',2102,state['episode'],0,'skip',0,4600,'boot',3600)
        self.assertEqual(req,self.engine.ask('child',2102,state['episode'],0,'skip',0,4600,'boot',3600))
        self.engine.decide(2102,req['id'],'deny',4600,'boot',3600)
        self.assertEqual(before,self.engine.state['learners'])
    def test_conflicting_parent_approval_and_failed_persistence(self):
        state=self.due();first=self.engine.ask('child',2102,state['episode'],0,'shorten',5,4600,'boot',3600);second=self.engine.ask('child',2103,state['episode'],0,'extend',5,4600,'boot',3600)
        before=copy.deepcopy(self.engine.state)
        with patch.object(self.engine,'write',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.engine.decide(2102,first['id'],'approve',4600,'boot',3600)
        self.assertEqual(self.engine.state,before)
        self.engine.decide(2102,first['id'],'approve',4600,'boot',3600)
        with self.assertRaises(ValueError):self.engine.decide(2103,second['id'],'approve',4600,'boot',3600)
    def test_disconnected_time_does_not_count_as_computer_use(self):
        self.engine.tick(self.config,{'child'},10,1000,'boot',0)
        self.engine.tick(self.config,set(),10,2000,'boot',1000)
        self.assertEqual(self.engine.view('child',2000,'boot',1000)['used_seconds'],10)
    def test_schema_bounds(self):
        for change in ({'enabled':'yes'},{'use_minutes':True},{'break_minutes':0},{'use_minutes':241},{'command':'sh'}):
            with self.assertRaises(ValueError):m.settings(dict(self.config['child'],**change))
class EngineTests(unittest.TestCase):
    def setUp(self):
        import importlib.machinery
        loader=importlib.machinery.SourceFileLoader('break_policy_test',str(ROOT/'parental/family-lab-policy'))
        spec=importlib.util.spec_from_loader(loader.name,loader);self.policy=importlib.util.module_from_spec(spec);loader.exec_module(self.policy)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.home=pathlib.Path(self.temp.name)
        for name in ('etc','data','run'):(self.home/name).mkdir()
        self.cfg={'subjects':{'child':{'uid':2101,'login':'child'}},'parents':{'2102':'Dad','2103':'Mom'},'browsers':[],'guards':{'959':'child'},'parent_helpers':{'dad':2102,'mom':2103}}
        policy=self.policy.defaults(['child']);policy['subjects']['child'].update(mode='monitor',breaks={'enabled':True,'use_minutes':1,'break_minutes':15},daily_minutes={day:0 for day in self.policy.DAYS})
        self.policy.atomic(self.home/'etc/enrollment.json',self.cfg);self.policy.atomic(self.home/'data/policy.json',{'revision':0,'policy':policy})
        self.engine=self.policy.Engine(self.home/'etc',self.home/'data',self.home/'run');self.now=1767607200
        self.wall=patch.object(self.policy.time,'time',side_effect=lambda:self.now);self.wall.start();self.addCleanup(self.wall.stop)
        self.clock=patch.object(self.policy,'boottime',return_value=100);self.clock.start();self.addCleanup(self.clock.stop)
        self.engine.tick({2101},self.now,0,100)
    def due(self):
        for i in range(1,7):self.engine.tick({2101},self.now,i*10,100)
        return self.engine.learner_request(2101,{'op':'get'})['break_status']
    def test_breaks_replace_daily_cap_but_preserve_bedtime(self):
        self.assertEqual(self.engine.status['child']['reason'],'')
        state=self.due();self.assertEqual(state['phase'],'due');self.assertEqual(self.engine.status['child']['reason'],'break')
        self.now+=12*3600;self.engine.tick({2101},self.now,70,100)
        self.assertEqual(self.engine.status['child']['reason'],'outside-hours')
    def test_guard_identity_and_parent_decisions(self):
        state=self.due()
        for uid in (2101,2102,9999):
            with self.assertRaises((ValueError,PermissionError)):self.engine.learner_request(uid,{'op':'guard-protected','episode':state['episode']})
        guarded=self.engine.learner_request(959,{'op':'guard-protected','episode':state['episode']});self.assertEqual(guarded['phase'],'break')
        with self.assertRaises(PermissionError):self.engine.request(959,{'op':'get'})
        with self.assertRaises(PermissionError):self.engine.request(2102,{'op':'break-protected','peer':'child','episode':state['episode']})
        request=self.engine.learner_request(959,{'op':'guard-ask','helper':'dad','change':'skip','minutes':0,'episode':state['episode'],'revision':0})
        self.assertEqual(len(self.engine.request(2102,{'op':'break-pending'})['requests']),1)
        self.assertEqual(self.engine.request(2103,{'op':'break-pending'})['requests'],[])
        with self.assertRaises(PermissionError):self.engine.request(2101,{'op':'break-decision','id':request['id'],'decision':'approve'})
        with self.assertRaises(ValueError):self.engine.request(2103,{'op':'break-decision','id':request['id'],'decision':'approve'})
        self.engine.request(2102,{'op':'break-decision','id':request['id'],'decision':'approve'})
        with self.assertRaises(ValueError):self.engine.learner_request(959,{'op':'guard-release'})
        self.engine.tick({2101},self.now,65,100)
        self.assertTrue(self.engine.learner_request(959,{'op':'guard-release'})['allowed'])
    def test_hibernate_requires_guard_identity_current_bedtime_and_verified_resume(self):
        for uid in (2101,2102,9999):
            with self.assertRaises((ValueError,PermissionError)):
                self.engine.learner_request(uid,{'op':'guard-hibernate','episode':'old'})
        with self.assertRaises(ValueError):self.engine.learner_request(959,{'op':'guard-hibernate','episode':'old'})
        self.now+=12*3600
        self.engine.current['policy']['subjects']['child']['mode']='enforce'
        self.engine.tick({2101},self.now,70,100)
        with self.assertRaises(ValueError):self.engine.learner_request(959,{'op':'guard-hibernate','episode':'old'})
        with patch.object(self.engine.bedtime_power,'ready',return_value=True):
            self.engine.tick({2101},self.now,80,100)
            state=self.engine.learner_request(959,{'op':'guard-get-secure'})
            episode=state['hibernate']['episode']
            self.assertTrue(self.engine.learner_request(959,{'op':'guard-hibernate','episode':episode})['accepted'])
        with patch.object(self.engine.bedtime_power,'ready',return_value=False):
            with self.assertRaises(ValueError):self.engine.learner_request(959,{'op':'guard-hibernate','episode':episode})
    def test_enforcement_gate_and_no_legacy_logout(self):
        candidate=copy.deepcopy(self.engine.current['policy']);candidate['subjects']['child']['mode']='enforce'
        (self.home/'etc/pam-ready').touch()
        with self.assertRaisesRegex(ValueError,'guard'):self.engine.request(2102,{'op':'apply','base_revision':0,'policy':candidate})
        state=self.due();self.engine.current['policy']=candidate;self.engine.tick({2101},self.now,1000,100)
        with patch.object(self.engine.guards,'sync') as sync,patch.object(self.policy.subprocess,'run') as command:
            self.engine.enforce(self.engine.status);sync.assert_called_once();command.assert_not_called()
    def test_bounded_guard_trial_does_not_enable_policy_and_requires_real_release(self):
        self.engine.current['policy']['subjects']['child']['mode']='off'
        with self.assertRaises(PermissionError):self.engine.request(2102,{'op':'guard-trial','peer':'child','seconds':15})
        self.engine.request(0,{'op':'guard-trial','peer':'child','seconds':15})
        self.engine.tick({2101},self.now,1,100)
        self.assertEqual(self.engine.current['policy']['subjects']['child']['mode'],'off')
        self.assertTrue(self.policy.read(self.home/'etc/gate.json')['subjects']['2101'])
        self.assertTrue(self.engine.status['child']['blocked']);self.assertTrue(self.engine.status['child']['guard_test'])
        state=self.engine.learner_request(959,{'op':'guard-get'})
        self.engine.learner_request(959,{'op':'guard-protected','episode':state['episode']})
        self.assertFalse(self.engine.learner_request(959,{'op':'guard-release'})['allowed'])
        self.now+=15
        with patch.object(self.policy,'boottime',return_value=115):
            self.engine.tick({2101},self.now,16,115)
            self.assertFalse(self.engine.status['child']['blocked']);self.assertIsNone(self.engine.guard_trial)
            self.assertFalse(self.policy.read(self.home/'etc/gate.json')['subjects']['2101'])
            receipt=self.policy.read(self.home/'data/guard-trial-result.json')
            self.assertTrue(receipt['protected']);self.assertFalse(receipt['release_checked'])
            self.assertTrue(self.engine.learner_request(959,{'op':'guard-release'})['allowed'])
            self.assertTrue(self.policy.read(self.home/'data/guard-trial-result.json')['release_checked'])
        self.assertEqual(self.engine.breaks.view('child',self.now,self.engine.boot,115)['used_seconds'],0)
    def test_long_trial_is_bounded_and_root_only(self):
        self.engine.current['policy']['subjects']['child']['mode']='off'
        with self.assertRaises(ValueError):self.engine.request(0,{'op':'guard-trial','peer':'child','seconds':601})
        result=self.engine.request(0,{'op':'guard-trial','peer':'child','seconds':600})
        self.assertEqual(result['maximum_seconds'],720)
        self.assertEqual(self.engine.current['policy']['subjects']['child']['mode'],'off')
    def test_break_skip_does_not_override_bedtime(self):
        state=self.due();self.engine.current['policy']['subjects']['child']['mode']='enforce'
        self.now+=12*3600;self.engine.tick({2101},self.now,70,100)
        req=self.engine.learner_request(2101,{'op':'break-request','helper':'dad','change':'skip','minutes':0,'episode':state['episode'],'revision':0})
        self.engine.request(2102,{'op':'break-decision','id':req['id'],'decision':'approve'})
        self.engine.tick({2101},self.now,75,100)
        self.assertTrue(self.engine.status['child']['blocked']);self.assertEqual(self.engine.status['child']['reason'],'outside-hours')

    def test_unknown_helper_stale_state_and_replay(self):
        state=self.due()
        request={'op':'break-request','helper':'other','change':'skip','minutes':0,'episode':state['episode'],'revision':0}
        with self.assertRaises(ValueError):self.engine.learner_request(2101,request)
        request['helper']='dad';self.engine.last_success=0
        with self.assertRaises(ValueError):self.engine.learner_request(2101,request)

if __name__=='__main__':unittest.main()
