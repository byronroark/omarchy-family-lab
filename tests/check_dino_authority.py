#!/usr/bin/env python3
"""Hermetic root-authority contract; no sleep, desktop or installed system changes."""
import copy
import importlib.machinery
import importlib.util
from pathlib import Path
import socket
import json
import tempfile
import threading
import unittest
from unittest.mock import patch

root=Path(__file__).resolve().parents[1]
loader=importlib.machinery.SourceFileLoader('policy',str(root/'parental/family-lab-policy'))
spec=importlib.util.spec_from_loader(loader.name,loader);m=importlib.util.module_from_spec(spec);loader.exec_module(m)

class DinoTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.finish=m.FinishEpisodes(self.base/'finish.json')
        self.finish.sync({'child'},1000,'boot',100)
        self.id=self.finish.rows['child']['id']
    def test_persistent_expiry_and_no_restart_reset(self):
        self.finish.sync({'child'},1299,'boot',399)
        self.assertEqual(self.finish.view('child',1299,'boot',399)['remaining'],1)
        reloaded=m.FinishEpisodes(self.base/'finish.json')
        reloaded.sync({'child'},1300,'boot',400)
        self.assertEqual(reloaded.view('child',1300,'boot',400)['phase'],'blocked')
        self.assertEqual(reloaded.rows['child']['id'],self.id)
    def test_late_save_once_and_rest(self):
        state=self.finish.action('child','save',self.id,1299,'boot',399)
        self.assertEqual(state['remaining'],180)
        with self.assertRaises(ValueError):self.finish.action('child','save',self.id,1300,'boot',400)
        self.assertEqual(self.finish.view('child',1479,'boot',579)['phase'],'blocked')
        state=self.finish.action('child','rest',self.id,1300,'boot',400)
        self.assertEqual(state['remaining'],0);self.assertFalse(state['power_enabled'])
    def test_reboot_and_clock_rollback_do_not_restore_time(self):
        self.assertEqual(self.finish.view('child',1001,'newboot',1)['remaining'],0)
        self.assertEqual(self.finish.view('child',900,'boot',400)['remaining'],0)
        self.finish.sync({'child'},1001,'newboot',1)
        self.assertEqual(self.finish.rows['child']['phase'],'blocked')
    def test_allowed_transition_invalidates_old_id(self):
        self.finish.sync(set(),1100,'boot',200)
        self.finish.sync({'child'},1200,'boot',300)
        self.assertNotEqual(self.finish.rows['child']['id'],self.id)
        with self.assertRaises(ValueError):self.finish.action('child','save',self.id,1200,'boot',300)
    def test_write_failure_does_not_acknowledge_or_mutate(self):
        before=copy.deepcopy(self.finish.rows)
        with patch.object(m,'atomic',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.finish.action('child','save',self.id,1001,'boot',101)
        self.assertEqual(self.finish.rows,before)
    def test_expired_and_arbitrary_actions_cannot_extend(self):
        with self.assertRaises(ValueError):self.finish.action('child','save',self.id,1300,'boot',400)
        with self.assertRaises(ValueError):self.finish.action('child','wake',self.id,1001,'boot',101)

    def test_corrupt_persisted_state_rejected(self):
        value=copy.deepcopy(self.finish.rows);value['child']['deadline']=True
        m.atomic(self.base/'bad.json',value)
        with self.assertRaises(ValueError):m.FinishEpisodes(self.base/'bad.json')

class LearnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        etc=self.base/'etc';data=self.base/'data';run=self.base/'run'
        for path in (etc,data,run):path.mkdir()
        self.config={'subjects':{'child':{'uid':2101,'login':'child'}},'parents':{'2102':'Dad'},'browsers':[]}
        m.atomic(etc/'enrollment.json',self.config)
        policy=m.defaults(['child']);policy['subjects']['child']['mode']='enforce'
        m.atomic(data/'policy.json',{'revision':0,'policy':policy})
        self.engine=m.Engine(etc,data,run)
        self.clock=patch.object(m,'boottime',return_value=100);self.clock.start();self.addCleanup(self.clock.stop)
        self.wall=patch.object(m.time,'time',return_value=1767650400);self.wall.start();self.addCleanup(self.wall.stop) # 22:00 UTC
        self.engine.tick({2101},monotonic=0)
    def test_uid_scope_fields_and_permission_separation(self):
        state=self.engine.learner_request(2101,{'op':'get'})
        for uid in (0,2102,9999):
            with self.assertRaises(PermissionError):self.engine.learner_request(uid,{'op':'get'})
        for req in ({'op':'pause'},{'op':'get','peer':'child'},{'op':'wake'},{'op':'save','episode':'old'}):
            with self.assertRaises(ValueError):self.engine.learner_request(2101,req)
        with self.assertRaises(PermissionError):self.engine.request(2101,{'op':'get'})
        self.assertFalse(state['power_enabled'])
    def test_save_does_not_change_existing_enforcement_or_policy(self):
        state=self.engine.learner_request(2101,{'op':'get'})
        original=copy.deepcopy(self.engine.state);policy=copy.deepcopy(self.engine.current)
        result=self.engine.learner_request(2101,{'op':'save','episode':state['episode']})
        self.assertEqual(result['remaining'],180)
        self.assertEqual(self.engine.state,original);self.assertEqual(self.engine.current,policy)
        with self.assertRaises(ValueError):self.engine.learner_request(2101,{'op':'save','episode':state['episode']})
    def test_stale_and_parent_updates_require_refresh(self):
        self.engine.last_success=0
        with self.assertRaises(ValueError):self.engine.learner_request(2101,{'op':'get'})
        self.engine.last_success=100;self.engine.generation+=1
        with self.assertRaises(ValueError):self.engine.learner_request(2101,{'op':'get'})
    def test_socket_uses_kernel_uid_not_payload(self):
        # A mocked enrollment uses the real test process UID; SO_PEERCRED remains real.
        import os
        self.config['subjects']['child']['uid']=os.getuid()
        m.atomic(self.engine.etc/'enrollment.json',self.config)
        server,client=socket.socketpair()
        worker=threading.Thread(target=m.handle_connection,args=(self.engine,server,True));worker.start()
        client.sendall(b'{"op":"get"}\n');reply=json.loads(client.recv(m.MAX_BYTES));client.close();worker.join()
        self.assertTrue(reply['ok']);self.assertFalse(reply['result']['power_enabled'])

if __name__=='__main__':unittest.main()
