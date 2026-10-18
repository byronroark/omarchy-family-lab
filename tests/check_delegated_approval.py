"""Real socket protocol + persistent job tests; no sudo, package installs or live SSH."""
import copy,importlib.util,json,os,pathlib,socket,sys,tempfile,threading,time,types,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'assistance'))
from family_approval import Broker,digest,send_message,read_message,serve_connection,peer_uid
from family_approval_actions import Actions
spec=importlib.util.spec_from_file_location('enrollment',ROOT/'setup/family_install.py');enroll=importlib.util.module_from_spec(spec);spec.loader.exec_module(enroll)
spec=importlib.util.spec_from_file_location('approval_setup',ROOT/'setup/approval_setup.py');setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
from check_enrollment import profile,key
class DelegatedApproval(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=pathlib.Path(self.temp.name);self.uid=os.getuid();self.calls=[];self.now=time.time()
        self.principals={str(self.uid):{'id':'mom','enabled':True,'scope':{'packages':['extra/jq'],'menus':[]}},str(self.uid+1):{'id':'dad','enabled':True,'scope':{'packages':['extra/jq'],'menus':[]}}}
        self.plan={'supported':True,'title':'Install jq','reason':'Test','requested':['extra/jq'],'transaction':['extra/jq=1.8.1-1']}
        self.broker=Broker(self.base,self.principals,lambda request,principal:copy.deepcopy(self.plan),lambda request,plan:self.calls.append((request,plan)) or 0,clock=lambda:self.now)
        self.request={'id':'a'*32,'time':time.time(),'message':'Please install jq','topic':'admin','software':{'action':'install','packages':['extra/jq']}}
    def tearDown(self):self.temp.cleanup()
    def prepare(self,uid=None):return self.broker.operation(self.uid if uid is None else uid,{'op':'prepare','request':self.request})
    def decide(self,review,choice='approve',uid=None):return self.broker.operation(self.uid if uid is None else uid,{'op':'decide','id':review['id'],'review':review['review'],'digest':review['digest'],'decision':choice})
    def test_approve_queue_run_exactly_once(self):
        review=self.prepare();self.request['software']['packages']=['extra/something-else']
        self.assertEqual(self.decide(review)['status'],'queued');self.assertFalse(self.calls)
        self.assertTrue(self.broker.run_next());self.assertFalse(self.broker.run_next())
        self.assertEqual(self.calls[0][0]['software']['packages'],['extra/jq'])
        self.assertEqual(json.loads((self.base/'results'/('a'*32+'.json')).read_text())['status'],'completed')
        with self.assertRaises(ValueError):self.decide(review)
    def test_deny_does_not_run(self):
        review=self.prepare();self.assertEqual(self.decide(review,'deny')['status'],'denied');self.assertFalse(self.broker.run_next());self.assertFalse(self.calls)
    def test_unauthorized_peer_and_cross_parent_decisions(self):
        with self.assertRaises(ValueError):self.prepare(self.uid+99)
        review=self.prepare()
        with self.assertRaises((ValueError,OSError)):self.decide(review,uid=self.uid+1)
    def test_digest_token_expiry_and_extra_fields(self):
        review=self.prepare()
        for field in ('digest','review'):
            bad=copy.deepcopy(review);bad[field]=('b'*64 if field=='digest' else 'b'*32)
            with self.assertRaises(ValueError):self.decide(bad)
        self.now+=301
        with self.assertRaises(ValueError):self.decide(review)
        with self.assertRaises(ValueError):self.broker.operation(self.uid,{'op':'status','id':'a'*32,'command':'sh'})
    def test_stale_plan_cannot_execute(self):
        review=self.prepare();self.plan['transaction']=['extra/jq=2.0-1']
        with self.assertRaises(ValueError):self.decide(review)
        self.assertFalse(self.calls)
    def test_change_after_queue_fails_without_execution(self):
        review=self.prepare();self.decide(review);self.plan['transaction']=['extra/jq=2.0-1'];self.broker.run_next();self.assertFalse(self.calls)
        self.assertEqual(json.loads(self.broker.receipt('a'*32).read_text())['status'],'failed')
    def test_revocation_before_start(self):
        review=self.prepare();self.decide(review);self.principals[str(self.uid)]['enabled']=False;self.broker.run_next();self.assertFalse(self.calls)
    def test_unsupported_can_be_denied_but_not_approved(self):
        self.plan['supported']=False;review=self.prepare()
        with self.assertRaises(ValueError):self.decide(review)
        self.assertEqual(self.decide(review,'deny')['status'],'denied')
    def test_recovery_never_replays_running_or_partial_commit(self):
        review=self.prepare();self.decide(review)
        self.broker.record(self.request,'running','mom');self.broker.recover();self.assertFalse(self.broker.run_next());self.assertFalse(self.calls)
        self.assertEqual(json.loads(self.broker.receipt('a'*32).read_text())['status'],'interrupted')
        # Existing technical receipts have a separate lifecycle and must be untouched.
        path=self.broker.receipt('b'*32);path.write_text('{"status":"running"}');self.broker.recover();self.assertEqual(path.read_text(),'{"status":"running"}')
    def test_existing_decision_returns_status_without_new_review(self):
        review=self.prepare();self.decide(review,'deny');result=self.prepare();self.assertTrue(result['already_decided']);self.assertEqual(result['status'],'denied')
    def test_parent_race_only_first_decision_wins(self):
        first=self.prepare();second=self.prepare(self.uid+1);self.decide(first)
        with self.assertRaises(ValueError):self.decide(second,uid=self.uid+1)
    def test_shared_technical_lock_prevents_overlap(self):
        review=self.prepare()
        with self.broker.lock():
            with self.assertRaises(BlockingIOError):self.decide(review)
        self.assertFalse(self.calls)
    def test_real_unix_peer_credentials(self):
        path=str(self.base/'socket');listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);listener.bind(path);listener.listen()
        def server():
            connection,_=listener.accept()
            with connection:self.assertEqual(peer_uid(connection),self.uid);serve_connection(connection,self.broker)
        thread=threading.Thread(target=server);thread.start()
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
            client.connect(path);send_message(client,{'op':'prepare','request':self.request});result=read_message(client)
        thread.join(3);listener.close();self.assertTrue(result['ok']);self.assertEqual(result['plan']['transaction'],self.plan['transaction'])
    def test_client_bridge_worker_protocol_end_to_end_without_ssh(self):
        import subprocess
        import family_approval_client as client_module
        path=str(self.base/'wire.sock');listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);listener.bind(path);listener.listen()
        bridge=self.base/'bridge';source=(ROOT/'assistance/family-approval-bridge').read_text().replace('/run/family-help-approval/control.sock',path);bridge.write_text(source)
        failures=[]
        def server():
            try:
                for _ in range(4):
                    connection,_=listener.accept()
                    with connection:serve_connection(connection,self.broker)
            except Exception as exc:failures.append(exc)
        thread=threading.Thread(target=server);thread.start();real_popen=subprocess.Popen
        def transport(args,**kwargs):
            self.assertEqual(args[0],'/usr/bin/ssh');self.assertIn('-T',args)
            env=dict(os.environ,PYTHONPATH=str(ROOT/'assistance'),SSH_ORIGINAL_COMMAND='')
            return real_popen(['/usr/bin/python3',str(bridge)],env=env,**kwargs)
        config={'capability':'approver','ssh_config':'not-used','approval_alias':'restricted-approver'}
        try:
            with patch.object(client_module.subprocess,'Popen',side_effect=transport):
                review=client_module.rpc(config,{'op':'prepare','request':self.request})
                self.assertEqual(client_module.decision(config,review,'approve')['status'],'queued')
                self.assertTrue(self.broker.run_next())
                self.assertEqual(client_module.rpc(config,{'op':'status','id':self.request['id']})['status'],'completed')
                with self.assertRaises(ValueError):client_module.decision(config,review,'approve')
            thread.join(5);self.assertFalse(thread.is_alive());self.assertFalse(failures);self.assertEqual(len(self.calls),1)
        finally:listener.close()
    def test_added_parent_preserves_existing_registry_and_technical_paths(self):
        p=profile();p.pop('dad');p.pop('mom');p['admin'].pop('identity_file');p['helper']={'id':'mom','kind':'mom','label':'Mom','login':'helper','host':'192.0.2.20','capability':'approver'};p['approval_scope']={'packages':[],'menus':[]};p['public_keys']={'approval':key(9)}
        original={'version':1,'principals':{'959':{'id':'otherparent','label':'Other','enabled':True,'scope':{'packages':[],'menus':[]}}}}
        desired=setup.desired_files(vars(enroll),p,960,original)
        registry=json.loads(desired['/etc/family-help/approvers.json'][0]);self.assertEqual(registry['principals']['959'],original['principals']['959']);self.assertIn('960',registry['principals'])
        self.assertNotIn('960',original['principals'])
        with tempfile.TemporaryDirectory() as folder:
            base=pathlib.Path(folder);state=base/'state/managed.json';tx=enroll.Files(base,state,staged=True)
            for name,(data,mode,link) in desired.items():tx.write(name,data,mode,link)
            tx.commit();again=enroll.Files(base,state,staged=True)
            for name,(data,mode,link) in desired.items():again.write(name,data,mode,link)
            self.assertFalse(again.changes)
    def test_scope_and_noninteractive_pinned_command(self):
        actions=Actions({'child':'learner','admin':'parent'},runner=lambda args,**kwargs:types.SimpleNamespace(stdout='extra/jq=1.8.1-1\n',returncode=0))
        planned=actions.plan(self.request,self.principals[str(self.uid)]);self.assertTrue(planned['supported'])
        other=copy.deepcopy(self.request);other['software']={'action':'update','packages':[]};self.assertFalse(actions.plan(other,self.principals[str(self.uid)])['supported'])
        other['software']={'action':'install','packages':['extra/unknown']};self.assertFalse(actions.plan(other,self.principals[str(self.uid)])['supported'])
        commands=[];actions.runner=lambda args,**kwargs:commands.append((args,kwargs)) or types.SimpleNamespace(returncode=0)
        with patch.object(pathlib.Path,'exists',return_value=False):self.assertEqual(actions.execute(self.request,planned),0)
        self.assertEqual(commands[0][0],['/usr/bin/pacman','-S','--needed','--noconfirm','--','extra/jq=1.8.1-1']);self.assertTrue(commands[0][1]['close_fds'])
    def test_approver_prompt_does_not_request_admin_identity(self):
        answers=iter(['mom','','approver','','','learner','','192.0.2.10','','parent','','192.0.2.20','','','','SHA256:'+('A'*43)])
        prompts=[]
        def answer(prompt):prompts.append(prompt);return next(answers)
        with patch('builtins.input',side_effect=answer),patch.object(enroll.pwd,'getpwuid',return_value=types.SimpleNamespace(pw_name='helper')):p=enroll.prompt_profile()
        self.assertEqual(enroll.capability(p),'approver');self.assertNotIn('identity_file',p['admin']);self.assertFalse(any('private key' in prompt.lower() for prompt in prompts))
    def test_request_fields_do_not_allow_commands_flags_or_paths(self):
        for software in ({'action':'install','packages':['--config=evil']},{'action':'install','packages':['/tmp/local.pkg']},{'action':'shell','packages':[]},{'action':'install','packages':['extra/jq'],'command':'id'}):
            bad=copy.deepcopy(self.request);bad['software']=software
            with self.assertRaises(ValueError):self.broker.operation(self.uid,{'op':'prepare','request':bad})
    def test_queued_without_job_after_crash_is_not_replayed(self):
        review=self.prepare();self.decide(review);(self.base/'approval-jobs'/('a'*32+'.json')).unlink();self.broker.recover()
        self.assertEqual(json.loads(self.broker.receipt('a'*32).read_text())['status'],'interrupted');self.assertFalse(self.broker.run_next())
    def test_executor_failure_recorded_and_cannot_retry(self):
        review=self.prepare();self.decide(review);self.broker.executor=lambda *args:23;self.broker.run_next()
        result=json.loads(self.broker.receipt('a'*32).read_text());self.assertEqual((result['status'],result['returncode']),('failed',23))
        with self.assertRaises(ValueError):self.decide(review)
    def test_untrusted_profile_paths_are_not_privileged_input(self):
        path=self.base/'profile.json';path.write_text(json.dumps(profile()));path.chmod(0o600)
        self.assertEqual(enroll.read_profile(path)['admin']['login'],'parent')
        link=self.base/'link';link.symlink_to(path)
        with self.assertRaises(OSError):enroll.read_profile(link)
        fifo=self.base/'fifo';os.mkfifo(fifo)
        with self.assertRaises(ValueError):enroll.read_profile(fifo)
        path.write_bytes(b'x'*65537)
        with self.assertRaises(ValueError):enroll.read_profile(path)
        path.write_text(json.dumps(profile()));path.chmod(0o666)
        with patch.object(enroll.os,'geteuid',return_value=0),patch.object(enroll.pwd,'getpwnam',return_value=types.SimpleNamespace(pw_uid=os.getuid())):
            with self.assertRaises(ValueError):enroll.read_profile(path)
    def test_mom_approver_bundle_has_no_admin_or_control_credentials(self):
        p=profile();p.pop('dad');p.pop('mom');p['admin'].pop('identity_file');p['helper']={'id':'mom','kind':'mom','label':'Mom','login':'helper','host':'192.0.2.20','capability':'approver'};p['approval_scope']={'packages':['extra/jq'],'menus':[]};p['public_keys']={'approval':key(9)}
        enroll.validate(p);files=enroll.helper_files(p,self.base,None,self.base/'keys');config=json.loads(files['.config/family-help/helper.json'][0]);ssh=files['.config/family-help/ssh.conf'][0].decode()
        self.assertNotIn('admin_alias',config);self.assertNotIn('view_alias',config);self.assertNotIn('control_alias',config);self.assertEqual(ssh.count('Host '),1);self.assertIn('User familyap-mom',ssh)
        desired=setup.desired_files(vars(enroll),p,960,{'version':1,'principals':{}})
        self.assertFalse(any('sudoers' in path or path.endswith('child.json') or path.endswith('teaching.json') or '/home/' in path for path in desired))
        self.assertIn(b'PermitTTY no',desired['/etc/ssh/sshd_config.d/41-family-help-mom.conf'][0]);self.assertIn(b'ForceCommand /usr/local/libexec/family-approval-bridge',desired['/etc/ssh/sshd_config.d/41-family-help-mom.conf'][0])
        bad=copy.deepcopy(p);bad['admin']['identity_file']='/a/private/key'
        with self.assertRaises(ValueError):enroll.validate(bad)
if __name__=='__main__':unittest.main()
