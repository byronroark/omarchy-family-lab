import datetime as dt
import importlib.util
from pathlib import Path
import tempfile
import unittest
import os

spec=importlib.util.spec_from_file_location('retention',Path(__file__).resolve().parents[1]/'integrations/family_activitywatch_retention.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
CUTOFF=dt.datetime(2026,10,13,tzinfo=dt.timezone.utc)


class RetentionTests(unittest.TestCase):
    def test_only_local_supported_buckets_and_expired_ids(self):
        calls=[]
        events=[{'id':1,'timestamp':'2026-10-12T00:00:00Z'}, {'id':2,'timestamp':CUTOFF.isoformat()}]
        def api(path,method='GET'):
            calls.append((path,method))
            if path=='buckets/':return {'local':{'type':'currentwindow','hostname':'test'},'foreign':{'type':'currentwindow','hostname':'other'},'other':{'type':'custom','hostname':'test'}}
            if method=='DELETE':events[:]=[e for e in events if not path.endswith('/'+str(e['id']))];return None
            return events.copy()
        self.assertEqual(m.prune(CUTOFF,True,api,'test'),1)
        self.assertEqual([c for c in calls if c[1]=='DELETE'],[('buckets/local/events/1','DELETE')])
        self.assertFalse(any('foreign' in p for p,_ in calls))

    def test_dry_run_never_deletes(self):
        def api(path,method='GET'):
            self.assertEqual(method,'GET')
            return {'b':{'type':'afkstatus','hostname':'test'}} if path=='buckets/' else [{'id':4,'timestamp':'2020-01-01T00:00:00Z'}]
        self.assertEqual(m.prune(CUTOFF,False,api,'test'),1)

    def test_invalid_identity_or_naive_timestamp(self):
        for event in [{'id':'../../x','timestamp':'2020-01-01T00:00:00Z'},{'id':1,'timestamp':'2020-01-01T00:00:00'}]:
            with self.assertRaises(ValueError):m.expired_ids([event],CUTOFF)

    def test_report_cleanup_preserves_other_files_and_symlinks(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            for name in ['report-old.md','report-new.md','observations.json']:(root/name).write_text('private')
            os.utime(root/'report-old.md',(0,0));os.utime(root/'observations.json',(0,0))
            (root/'report-link.md').symlink_to(root/'observations.json')
            self.assertEqual(m.prune_reports(root,CUTOFF,True),1)
            self.assertTrue((root/'observations.json').exists())
            self.assertTrue((root/'report-new.md').exists())


if __name__=='__main__':unittest.main()
