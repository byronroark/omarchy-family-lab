"""Parent break-card schema and private reports without SSH or system changes."""
import copy,datetime as dt,json,os,pathlib,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'assistance'))
import family_policy_client as client
class ClientTests(unittest.TestCase):
    def test_break_card_contains_only_fixed_fields(self):
        data={'id':'a'*32,'time':dt.datetime.now(dt.timezone.utc).timestamp(),'topic':'break','message':'Skip this break','break_request':{'peer':'child','episode':'b'*32,'revision':0,'change':'skip','minutes':0}}
        self.assertEqual(client.validate_card(data),data)
        for field,value in [('minutes',True),('change','sudo'),('episode','../file'),('revision',-1)]:
            bad=copy.deepcopy(data);bad['break_request'][field]=value
            with self.assertRaises(ValueError):client.validate_card(bad)
        with self.assertRaises(ValueError):client.validate_card(dict(data,command='sh'))
        with self.assertRaises(ValueError):client.validate_card(dict(data,time=data['time']-901))
    def test_private_report_and_empty_coverage_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            summary={'coverage':'No application or website observations','timezone':'America/New_York','days':{}}
            path=client.report(summary,'child',directory);self.assertEqual(path.stat().st_mode&0o777,0o600);self.assertIn('No observations',path.read_text())
            summary['days']={'2026-10-18':{'child':3600,'other':9999}}
            path=client.report(summary,'child',directory);text=path.read_text();self.assertIn('60.0',text);self.assertNotIn('other',text)
            with self.assertRaises(ValueError):client.report(summary,'../child',directory)
if __name__=='__main__':unittest.main()
