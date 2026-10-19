"""Simulated clocks and mocked logind; never sleeps the test machine."""
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bedtime', ROOT/'parental/family_bedtime.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = pathlib.Path(self.temp.name)/'state.json'
        self.read = lambda p: json.loads(p.read_text())
        self.write = lambda p,v: p.write_text(json.dumps(v))
        self.b = m.Bedtime(self.path,self.read,self.write,self.path.with_name('ready'))
        self.ready = patch.object(m.Bedtime,'ready',return_value=True)
        self.ready.start(); self.addCleanup(self.ready.stop)
        self.row = {'mode':'enforce','blocked':True,'reason':'outside-hours','logged_in':True}
        self.b.sync({'child':self.row},'boot',100,100)

    def enforce(self, elapsed):
        self.b.protected('child',elapsed)
        with patch.object(m.subprocess,'run') as run:
            self.b.enforce('child',self.row,elapsed,lambda *a:None)
        return run

    def test_full_five_minutes_and_fixed_logind_operation(self):
        self.enforce(399).assert_not_called()
        run = self.enforce(400); run.assert_called_once()
        self.assertEqual(run.call_args.args[0][-3:],['Hibernate','b','false'])

    def test_now_requires_matching_episode_and_protected_screen(self):
        episode = self.b.view('child',100)['episode']
        with self.assertRaises(ValueError): self.b.request('child',episode,100)
        self.b.protected('child',100)
        with self.assertRaises(ValueError): self.b.request('child','old',100)
        self.b.request('child',episode,100)
        self.enforce(101).assert_called_once()

    def test_restart_does_not_reset_countdown_or_assume_secure(self):
        self.b = m.Bedtime(self.path,self.read,self.write,self.path.with_name('ready'))
        self.b.sync({'child':self.row},'boot',300,300)
        self.assertEqual(self.b.view('child',300)['remaining_seconds'],100)
        with patch.object(m.subprocess,'run') as run:
            self.b.enforce('child',self.row,400,lambda *a:None)
        run.assert_not_called()

    def test_real_wake_starts_new_five_minutes(self):
        self.b.sync({'child':self.row},'boot',1400,400)
        self.assertEqual(self.b.view('child',1400)['remaining_seconds'],300)
        self.assertNotIn('child',self.b.secure)

    def test_parent_exception_and_breaks_cancel_power_timer(self):
        for change in ({'blocked':False},{'reason':'break'},{'mode':'monitor'},{'logged_in':False}):
            row = dict(self.row,**change)
            with patch.object(m.subprocess,'run') as run:
                self.b.protected('child',400)
                self.b.enforce('child',row,400,lambda *a:None)
            run.assert_not_called()
            self.b.sync({'child':row},'boot',400,400)
            self.assertFalse(self.b.view('child',400)['enabled'])
            self.b.sync({'child':self.row},'boot',100,100)

    def test_failure_keeps_lock_and_backs_off(self):
        self.b.protected('child',400)
        with patch.object(m.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'busctl')):
            self.b.enforce('child',self.row,400,lambda *a:None)
        self.assertIn('protected',self.b.view('child',400)['error'])
        self.enforce(401).assert_not_called()
        self.enforce(460).assert_called_once()

    def test_no_acceptance_no_power(self):
        with patch.object(m.Bedtime,'ready',return_value=False):
            self.enforce(400).assert_not_called()
            self.assertFalse(self.b.view('child',400)['enabled'])


if __name__ == '__main__': unittest.main()
