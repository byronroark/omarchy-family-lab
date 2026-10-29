import importlib.util,unittest,tempfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('pending',Path(__file__).resolve().parents[1]/'integrations/family_discord_pending.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_delay_offline_and_expiration(self):
  self.assertFalse(m.due(100,279));self.assertTrue(m.due(100,280))
  self.assertFalse(m.due(100,120,119));self.assertTrue(m.due(100,170,100))
  self.assertFalse(m.due(100,1000));self.assertFalse(m.due(200,100))
 def test_restart_cannot_resend_claimed_card(self):
  with tempfile.TemporaryDirectory() as root:
   p=Path(root)/'relay.db';a=m.Pending(p)
   self.assertTrue(a.claim('break','abc',{'created':1}));a.db.close()
   b=m.Pending(p);self.assertFalse(b.claim('break','abc',{'created':1}))
   b.sent('break','abc',123);b.finish('break','abc','denied');self.assertEqual(b.load('break','abc')[1],'denied')
if __name__=='__main__':unittest.main()
