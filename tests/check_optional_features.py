"""Optional integrations, using synthetic ActivityWatch data only."""
import datetime as dt
import importlib.util
import importlib.machinery
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


aw = module('aw', 'integrations/family_activitywatch.py')
setup = module('optional_setup', 'setup/features_setup.py')
BASE = dt.datetime(2026, 10, 24, tzinfo=dt.timezone.utc).timestamp()


def event(start, duration, **data):
    return {'timestamp': dt.datetime.fromtimestamp(BASE + start, dt.timezone.utc).isoformat(),
            'duration': duration, 'data': data}


class ActivityTests(unittest.TestCase):
    def config(self):
        return {'enabled': True, 'acknowledge_raw_storage': True, 'web_bucket': 'web',
                'afk_bucket': 'afk', 'window_bucket': 'window', 'browser_apps': ['firefox']}

    def test_active_web_intersects_window_and_non_idle_without_double_counting(self):
        web = [event(0, 600, url='https://example.org/private?q=secret', title='SECRET TITLE', incognito=False)]
        idle = [event(0, 300, status='not-afk'), event(300, 300, status='afk')]
        windows = [event(0, 120, app='firefox'), event(120, 480, app='Steam')]
        result = aw.normalize(web, idle, windows, BASE, BASE + 600, ['firefox'])
        self.assertEqual(len(result['observations']), 2)
        self.assertEqual(result['observations'][0]['domain'], 'example.org')
        self.assertIsNone(result['observations'][1]['domain'])
        text = json.dumps(result)
        for secret in ('SECRET TITLE', '?q=', '/private', 'https:'):
            self.assertNotIn(secret, text)
        total = sum(aw.timestamp(row['end']) - aw.timestamp(row['start']) for row in result['observations'])
        self.assertEqual(total, 300)

    def test_private_missing_metadata_and_internal_urls_have_no_domain(self):
        for fields in ({'incognito': True, 'url': 'https://private.example'},
                       {'url': 'https://unknown.example'},
                       {'incognito': False, 'url': 'chrome://settings'},
                       {'incognito': False, 'url': 'https://user:password@example.org'}):
            data = aw.normalize([event(0, 60, **fields)], [event(0, 60, status='not-afk')],
                                [event(0, 60, app='firefox')], BASE, BASE + 60, ['firefox'])
            self.assertIsNone(data['observations'][0]['domain'])

    def test_gaps_unknown_and_cross_midnight_is_clipped(self):
        result = aw.normalize([], [event(-60, 120, status='not-afk')],
                              [event(-60, 120, app='Editor')], BASE, BASE + 600, [])
        self.assertEqual(len(result['observations']), 1)
        self.assertEqual(aw.timestamp(result['observations'][0]['start']), BASE)
        self.assertEqual(aw.timestamp(result['observations'][0]['end']), BASE + 60)
        self.assertFalse(aw.normalize([], [], [], BASE, BASE + 60, [])['observations'])

    def test_overlaps_and_bad_durations_rejected(self):
        for duration in (True, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError): aw.intervals([event(0, duration, app='Editor')], BASE, BASE + 60, 'window')
        with self.assertRaises(ValueError):
            aw.intervals([event(0, 60, app='Editor'), event(30, 60, app='Editor')], BASE, BASE + 120, 'window')

    def test_disabled_ack_and_arbitrary_hosts_rejected(self):
        for config in ({'enabled': False}, dict(self.config(), acknowledge_raw_storage=False), dict(self.config(), host='remote')):
            with self.assertRaises(ValueError): aw.settings(config)

    def test_bounded_metadata_checked_readonly_api(self):
        paths = []
        def fetch(path, port):
            paths.append(path)
            if path == 'buckets/':
                return {'web': {'type': 'web.tab.current'}, 'afk': {'type': 'afkstatus'}, 'window': {'type': 'currentwindow'}}
            return []
        result = aw.collect(self.config(), BASE, BASE + 86400, fetch)
        self.assertFalse(result['observations'])
        self.assertEqual(len(paths), 4)
        self.assertIn('limit=10001', paths[1])
        with self.assertRaises(ValueError): aw.collect(self.config(), BASE, BASE + 86400, lambda *args: {})
        with self.assertRaises(ValueError): aw.NoRedirect().redirect_request(None, None, None, None, None, None)

    def test_real_loopback_api_to_markdown_and_existing_report_role(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import threading
        paths=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                paths.append(self.path)
                if self.path=='/api/0/buckets/':
                    body={'web':{'type':'web.tab.current'},'afk':{'type':'afkstatus'},'window':{'type':'currentwindow'}}
                elif '/buckets/web/' in self.path:
                    body=[event(0,120,url='https://example.org/SECRET?q=HIDDEN',title='PRIVATE TITLE',incognito=False)]
                elif '/buckets/afk/' in self.path: body=[event(0,120,status='not-afk')]
                else: body=[event(0,120,app='firefox')]
                raw=json.dumps(body).encode();self.send_response(200);self.end_headers();self.wfile.write(raw)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            loader=importlib.machinery.SourceFileLoader('report_adapter',str(ROOT/'scripts/family-lab-report'))
            spec=importlib.util.spec_from_loader(loader.name,loader)
            report=importlib.util.module_from_spec(spec);loader.exec_module(report)
            with tempfile.TemporaryDirectory() as folder:
                report.CONFIG=Path(folder)/'config.json'
                config=dict(self.config(),port=server.server_port)
                report.CONFIG.write_text(json.dumps({'reporting':{'enabled':True,'provider':'activitywatch','activitywatch':config}}))
                text=report.render('2026-10-24','2026-10-24')
                self.assertIn('example.org',text);self.assertIn('**2.0 minutes**',text)
                self.assertIn('ActivityWatch',text)
                for secret in ('SECRET','HIDDEN','PRIVATE TITLE'): self.assertNotIn(secret,text)
                self.assertEqual(len(paths),4)
        finally:
            server.shutdown();server.server_close();thread.join()


class SetupTests(unittest.TestCase):
    def test_adguard_digest_and_minimal_bindings(self):
        data = setup.adguard_compose('adguard/adguardhome@sha256:' + 'a' * 64, '192.168.50.2')
        service = data['services']['adguardhome']
        self.assertEqual(len(service['ports']), 4)
        self.assertIn('127.0.0.1:3000:3000/tcp', service['ports'])
        self.assertNotIn('privileged', service); self.assertNotIn('network_mode', service)
        for image, bind in [('adguard/adguardhome:latest', '192.168.50.2'),
                            ('adguard/adguardhome@sha256:' + 'a' * 64, '0.0.0.0')]:
            with self.assertRaises(ValueError): setup.adguard_compose(image, bind)

    def test_plan_writes_nothing_and_explicit_apply_preserves_other_configuration(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(Path, 'home', return_value=Path(folder)), patch.object(os, 'geteuid', return_value=1000):
            setup.main(['configure'])
            self.assertFalse(list(Path(folder).iterdir()))
            config = Path(folder) / '.config/family-lab/config.json'
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({'notify_aliases': {'dad': 'private-alias'}, 'reporting': {'allowed_helpers': ['dad']}}))
            setup.main(['configure', '--activitywatch', 'on', '--web-bucket', 'web', '--window-bucket', 'window',
                        '--afk-bucket', 'afk', '--browser-app', 'firefox', '--acknowledge-raw-activitywatch-storage', '--apply'])
            result = json.loads(config.read_text())
            self.assertEqual(result['notify_aliases'], {'dad': 'private-alias'})
            self.assertEqual(result['reporting']['allowed_helpers'], ['dad'])
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            self.assertTrue((Path(folder) / '.local/bin/family-lab-report').is_file())
            self.assertFalse(result['integrations']['adguard_home']['enabled'])

    def test_adguard_output_requires_apply_and_keeps_existing_files(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(os,'geteuid',return_value=1000):
            output=Path(folder)/'adguard.compose.json'
            args=['adguard-compose','--image','adguard/adguardhome@sha256:'+'a'*64,'--dns-bind','192.168.50.2','--output',str(output)]
            setup.main(args);self.assertFalse(output.exists())
            setup.main(args+['--apply']);self.assertTrue(output.is_file())
            self.assertEqual(output.stat().st_mode&0o777,0o600)
            with self.assertRaises(ValueError):setup.main(args+['--apply'])


if __name__ == '__main__': unittest.main()
