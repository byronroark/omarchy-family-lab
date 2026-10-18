#!/usr/bin/env python3
"""Policy tests are hermetic. Never install PAM, terminate a user, or edit browser settings."""
import copy
import contextlib
import io
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
loader=importlib.machinery.SourceFileLoader('policy',str(ROOT/'parental/family-lab-policy'))
spec=importlib.util.spec_from_loader(loader.name,loader);m=importlib.util.module_from_spec(spec);loader.exec_module(m)

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name);self.etc=self.path/'etc';self.data=self.path/'data';self.runtime=self.path/'run'
        for d in (self.etc,self.data,self.runtime):d.mkdir()
        self.cfg={'subjects':{'alex':{'uid':2101,'login':'child'}},'parents':{'2102':'Dad','2103':'Mom'},'browsers':[]}
        m.atomic(self.etc/'enrollment.json',self.cfg)
        m.atomic(self.data/'policy.json',{'revision':0,'policy':m.defaults(self.cfg['subjects'])})
        self.engine=m.Engine(self.etc,self.data,self.runtime)
        self.now=1767607200.0 # 2026-01-05 10:00 UTC
    def rejected(self,req,uid=2102):
        with self.assertRaises((ValueError,PermissionError,KeyError)):
            self.engine.request(uid,req)
    def apply(self,mode='monitor',minutes=1):
        policy=copy.deepcopy(self.engine.current['policy']);s=policy['subjects']['alex'];s['mode']=mode
        s['daily_minutes']={d:minutes for d in m.DAYS}
        return self.engine.request(2102,{'op':'apply','base_revision':self.engine.current['revision'],'policy':policy})
    def test_off_and_parent_authorization(self):
        self.engine.tick({2101},self.now,0,0)
        row=self.engine.tick({2101},self.now+5,5,5)['alex']
        self.assertEqual(row['used_seconds'],0);self.assertFalse(row['blocked'])
        for uid in (2101,9999):self.rejected({'op':'get'},uid)
        for uid in (0,2102,2103):self.assertEqual(self.engine.request(uid,{'op':'get'})['revision'],0)
        self.cfg['parents'].pop('2102');m.atomic(self.etc/'enrollment.json',self.cfg)
        self.rejected({'op':'get'},2102)
    def test_conflicts_undo_and_no_remote_enrollment(self):
        self.apply();self.rejected({'op':'undo','base_revision':0})
        policy=copy.deepcopy(self.engine.current['policy']);policy['subjects']['root']=policy['subjects']['alex']
        self.rejected({'op':'apply','base_revision':1,'policy':policy})
        self.engine.request(2103,{'op':'undo','base_revision':1})
        self.assertEqual(self.engine.current['revision'],2)
        self.assertEqual(self.engine.current['policy']['subjects']['alex']['mode'],'off')
        self.rejected({'op':'exec','command':'id'})
    def test_monitor_counts_once_excludes_suspend_and_persists(self):
        self.apply();self.engine.tick({2101},self.now,100,100)
        row=self.engine.tick({2101},self.now+5,105,105)['alex']
        self.assertEqual(row['used_seconds'],5)
        # CLOCK_MONOTONIC excludes sleep; BOOTTIME advances during sleep.
        row=self.engine.tick({2101},self.now+3605,105,3705)['alex']
        self.assertEqual(row['used_seconds'],5)
        reloaded=m.Engine(self.etc,self.data,self.runtime)
        row=reloaded.tick({2101},self.now+3606,106,3706)['alex']
        self.assertEqual(row['used_seconds'],5)
        self.assertFalse(row['blocked'])
    def test_enforcement_requires_pam_grace_not_restarted(self):
        self.rejected({'op':'apply','base_revision':0,'policy':dict(m.defaults(['alex']),subjects={'alex':dict(m.defaults(['alex'])['subjects']['alex'],mode='enforce')})})
        (self.etc/'pam-ready').touch();self.apply('enforce',0)
        row=self.engine.tick({2101},self.now,0,0)['alex']
        self.assertTrue(row['blocked']);self.assertEqual(row['grace_seconds'],120)
        row=self.engine.tick({2101},self.now+60,5,60)['alex'];self.assertEqual(row['grace_seconds'],60)
        reloaded=m.Engine(self.etc,self.data,self.runtime)
        row=reloaded.tick({2101},self.now+121,6,121)['alex'];self.assertEqual(row['grace_seconds'],0)
    def test_extra_does_not_override_bedtime_pause_expires(self):
        (self.etc/'pam-ready').touch();self.apply('enforce',0)
        self.engine.request(2102,{'op':'extra','peer':'alex','minutes':15})
        # Grant uses real current date; patch current time to the fixture for deterministic day.
        with patch.object(m.time,'time',return_value=self.now):
            self.engine.request(2102,{'op':'extra','peer':'alex','minutes':15})
        row=self.engine.tick({2101},self.now,0,0)['alex'];self.assertFalse(row['blocked'])
        night=self.now+12*3600
        row=self.engine.tick({2101},night,5,5)['alex'];self.assertTrue(row['blocked'])
        with patch.object(m.time,'time',return_value=night),patch.object(m,'boottime',return_value=5):
            self.engine.request(2103,{'op':'pause','peer':'alex','minutes':1})
        self.assertFalse(self.engine.tick({2101},night+30,10,35)['alex']['blocked'])
        self.assertTrue(self.engine.tick({2101},night+61,11,66)['alex']['blocked'])
    def test_schema_browser_boundaries(self):
        for change in ({'grace_seconds':0},{'daily_minutes':{'mon':True}},{'hours':{d:[['22:00','08:00']] for d in m.DAYS}}):
            policy=m.defaults(['alex']);policy['subjects']['alex'].update(change)
            self.rejected({'op':'apply','base_revision':0,'policy':policy})
        policy=m.defaults(['alex']);policy['subjects']['alex']['browser']['enabled']=True
        self.rejected({'op':'apply','base_revision':0,'policy':policy})
        self.engine.config['browsers']=['chromium']
        policy['subjects']['alex']['browser']['blocked']=['https://example.org/private?q=secret']
        self.rejected({'op':'apply','base_revision':0,'policy':policy})
        policy['subjects']['alex']['browser']['blocked']=['example.org']
        self.engine.request(2102,{'op':'apply','base_revision':0,'policy':policy})
        with patch.object(m,'atomic') as write,patch.object(Path,'is_dir',return_value=True),patch.object(Path,'exists',return_value=False):
            self.engine.browser()
            self.assertEqual(write.call_args.args[0],Path('/etc/chromium/policies/managed/family-lab.json'))
            self.assertEqual(write.call_args.args[1]['URLBlocklist'],['example.org'])
    def test_pam_stale_and_unmanaged_recovery(self):
        account=type('Account',(),{'pw_uid':2101,'pw_gid':2101})()
        wheel=type('Group',(),{'gr_mem':['admin'],'gr_gid':10})()
        m.atomic(self.etc/'gate.json',{'subjects':{'2101':True}})
        (self.etc/'pam-ready').touch();self.apply('enforce',30)
        self.engine.tick(set(),self.now,10,10)
        with patch.object(m.pwd,'getpwnam',return_value=account),patch.object(m.grp,'getgrnam',return_value=wheel):
            self.assertTrue(m.login_allowed('child',self.etc,self.runtime,boot=self.engine.boot,elapsed=15))
            self.assertFalse(m.login_allowed('child',self.etc,self.runtime,boot=self.engine.boot,elapsed=31))
            self.assertFalse(m.login_allowed('child',self.etc,self.runtime,boot='new-boot',elapsed=15))
            # Admin immunity is checked before reading even a corrupt enrollment.
            (self.etc/'enrollment.json').write_text('broken')
            self.assertTrue(m.login_allowed('admin',self.etc,self.runtime))
    def test_retention_clock_rollback_and_file_modes(self):
        self.apply()
        for day in range(35):self.engine.tick({2101},self.now+day*86400,day*5,day*5)
        self.assertEqual(len(self.engine.state['days']),30)
        high=max(self.engine.state['days'])
        self.engine.tick({2101},self.now,180,180)
        self.assertEqual(max(self.engine.state['days']),high)
        self.assertEqual((self.data/'usage.json').stat().st_mode & 0o077,0)
        self.assertEqual((self.runtime/'status.json').stat().st_mode & 0o777,0o644)
    def test_local_recovery_disables_gate_and_preserves_bad_usage(self):
        (self.etc/'pam-ready').touch();self.apply('enforce',0)
        self.engine.tick(set(),self.now,0,0)
        (self.data/'usage.json').write_text('corrupt')
        with patch.object(m.subprocess,'run') as run, contextlib.redirect_stdout(io.StringIO()):
            m.recover(self.etc,self.data,self.runtime)
            self.assertEqual(run.call_args.args[0],['/usr/bin/systemctl','stop','family-lab-policy.service'])
        self.assertFalse(m.read(self.etc/'gate.json')['subjects']['2101'])
        self.assertEqual(m.read(self.data/'policy.json')['policy']['subjects']['alex']['mode'],'off')
        self.assertTrue((self.data/'usage.before-recovery.json').exists())
        self.assertTrue((self.data/'policy.before-recovery.json').exists())

    def test_wire_schema(self):
        # Fake socket tests protocol bounds without a real socket or root action.
        class Connection:
            def __init__(self,payload):self.payload=payload
            def settimeout(self,x):pass
            def recv(self,n):
                out=self.payload[:n];self.payload=self.payload[n:];return out
        self.assertEqual(m.read_message(Connection(b'{"op":"get"}\n')),{'op':'get'})
        for payload in (b'x'*(m.MAX_BYTES+1),b'{}\n{}\n',b'bad\n'):
            with self.assertRaises(ValueError):m.read_message(Connection(payload))
    def test_real_socket_peer_identity(self):
        # socketpair uses temporary kernel endpoints only; no listener or service install.
        actual=os.getuid()
        if actual==0:
            self.skipTest('Root is intentionally the local recovery authority')
        self.cfg['parents'][str(actual)]='Enrolled parent'
        m.atomic(self.etc/'enrollment.json',self.cfg)
        for payload,expected in (({'op':'get'},True),({'op':'get','parent':'Mom'},False)):
            server,client=socket.socketpair()
            thread=threading.Thread(target=m.handle_connection,args=(self.engine,server))
            thread.start();client.sendall(json.dumps(payload).encode()+b'\n')
            response=json.loads(client.recv(m.MAX_BYTES));client.close();thread.join(5)
            self.assertEqual(response['ok'],expected)
        self.cfg['parents'].pop(str(actual));m.atomic(self.etc/'enrollment.json',self.cfg)
        server,client=socket.socketpair()
        thread=threading.Thread(target=m.handle_connection,args=(self.engine,server));thread.start()
        response=json.loads(client.recv(m.MAX_BYTES));client.close();thread.join(5)
        self.assertFalse(response['ok'])
    def test_expiring_site_exception_and_audit(self):
        self.engine.config['browsers']=['chromium']
        policy=m.defaults(['alex']);policy['subjects']['alex']['browser']['enabled']=True
        self.engine.request(2102,{'op':'apply','base_revision':0,'policy':policy})
        with patch.object(m.time,'time',return_value=self.now),patch.object(m,'boottime',return_value=10):
            self.engine.request(2103,{'op':'allow-site','peer':'alex','domain':'example.org','minutes':1})
        self.assertIn('example.org',self.engine.state['sites'])
        self.engine.tick(set(),self.now+61,20,71)
        self.assertNotIn('example.org',self.engine.state['sites'])
        events=self.engine.request(2102,{'op':'history'})['events']
        self.assertTrue(any(row['parent']=='Mom' and row['action']=='allow-site' for row in events))
    def test_session_termination_is_fixed_enrolled_uid_after_grace_only(self):
        (self.etc/'pam-ready').touch();self.apply('enforce',0)
        with patch.object(m.subprocess,'run') as run:
            waiting=self.engine.tick({2101},self.now,0,0)
            self.engine.enforce(waiting);run.assert_not_called()
            expired=self.engine.tick({2101},self.now+121,5,121)
            self.engine.enforce(expired)
            self.assertEqual(run.call_args.args[0],['/usr/bin/loginctl','terminate-user','2101'])
            self.engine.enforce(expired);self.assertEqual(run.call_count,1)
        with patch.object(m.subprocess,'run') as run:
            expired['alex']['mode']='monitor';self.engine.last_terminated={}
            self.engine.enforce(expired);run.assert_not_called()

    def test_root_state_schema_no_shell_and_session_enumeration(self):
        rows=[{'uid':2101,'class':'manager'},{'uid':2101,'class':'user'},
              {'uid':2101,'class':'user'},{'uid':2102,'class':'user-light'}]
        completed=subprocess.CompletedProcess([],0,json.dumps(rows))
        with patch.object(m.subprocess,'run',return_value=completed) as run:
            self.assertEqual(m.sessions(),{2101,2102})
            self.assertEqual(run.call_args.args[0],['/usr/bin/loginctl','list-sessions','--json=short'])
        self.rejected({'op':'apply','base_revision':True,'policy':m.defaults(['alex'])})
        self.rejected({'op':'extra','peer':'alex; id','minutes':15})
        self.rejected({'op':'pause','peer':'alex','minutes':121})
    def test_failed_policy_write_keeps_conservative_login_gate(self):
        (self.etc/'pam-ready').touch()
        original=m.atomic
        def broken(path,*args,**kwargs):
            if path==self.data/'policy.json':
                raise OSError('Synthetic disk write failure')
            return original(path,*args,**kwargs)
        with patch.object(m,'atomic',side_effect=broken),self.assertRaises(OSError):
            self.apply('enforce',0)
        self.assertTrue(m.read(self.etc/'gate.json')['subjects']['2101'])
        self.assertEqual(self.engine.current['revision'],0)

    def test_new_pause_invalidates_a_queued_termination(self):
        (self.etc/'pam-ready').touch();self.apply('enforce',0)
        self.engine.tick({2101},self.now,0,0)
        expired=self.engine.tick({2101},self.now+121,5,121)
        with patch.object(m.time,'time',return_value=self.now+121),patch.object(m,'boottime',return_value=121):
            self.engine.request(2102,{'op':'pause','peer':'alex','minutes':15})
        with patch.object(m.subprocess,'run') as run:
            self.engine.enforce(expired);run.assert_not_called()

    def test_parent_menu_ssh_fixed_alias_and_no_exec_operation(self):
        loader=importlib.machinery.SourceFileLoader('parent_menu',str(ROOT/'scripts/family-lab-parent'))
        spec=importlib.util.spec_from_loader(loader.name,loader);module=importlib.util.module_from_spec(spec);loader.exec_module(module)
        module.CONFIG=self.path/'parent-config.json';module.CONFIG.write_text(json.dumps({'policy_aliases':{'alex':'child-policy'}}))
        def fake(args,**kw):
            self.assertEqual(args[-1],'child-policy');self.assertNotIn('shell',kw)
            kw['stdout'].write(b'{"revision":0}');kw['stdout'].flush()
        with patch.object(module.subprocess,'run',side_effect=fake):
            self.assertEqual(module.ask('alex',{'op':'get'}),{'revision':0})
        with self.assertRaises(ValueError):module.ask('unknown',{'op':'get'})
    def test_installer_help_and_no_changes_by_default(self):
        result=subprocess.run([sys.executable,str(ROOT/'scripts/install-parental-controls')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('Dry run only',result.stdout)

if __name__=='__main__':unittest.main()
