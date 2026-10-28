"""Prune local ActivityWatch events and Family Lab reports after 14 days.

Only local-host window, idle and browser buckets are eligible. No raw data is
logged. Events whose starting timestamp predates the cutoff are removed whole,
including long merged events crossing the cutoff. No database backups are made.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import socket
import urllib.parse
import urllib.request

TYPES = {'currentwindow', 'afkstatus', 'web.tab.current'}
LIMIT = 2 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('ActivityWatch redirects are refused')


def request(path, method='GET'):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    req = urllib.request.Request('http://127.0.0.1:5600/api/0/' + path, method=method)
    with opener.open(req, timeout=10) as response:
        raw = response.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('ActivityWatch response exceeds retention limit')
    return json.loads(raw) if raw else None


def expired_ids(events, cutoff):
    if not isinstance(events, list) or len(events) > 1000:
        raise ValueError('Invalid retention event batch')
    ids = []
    for event in events:
        event_id = event.get('id')
        stamp = dt.datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
        if type(event_id) is not int or event_id < 0 or stamp.tzinfo is None:
            raise ValueError('Invalid retention event identity or timestamp')
        if stamp < cutoff:
            ids.append(event_id)
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate retention event IDs')
    return ids


def prune(cutoff, apply=False, api=request, hostname=None):
    hostname = hostname or socket.gethostname()
    metadata = api('buckets/')
    if not isinstance(metadata, dict) or len(metadata) > 1000:
        raise ValueError('Invalid bucket metadata')
    total = 0
    for bucket, row in metadata.items():
        if row.get('type') not in TYPES or row.get('hostname') != hostname:
            continue
        base = 'buckets/' + urllib.parse.quote(bucket, safe='') + '/events'
        query = urllib.parse.urlencode({'end': cutoff.isoformat(), 'limit': 1000})
        previous = None
        for _ in range(100):
            ids = expired_ids(api(base + '?' + query), cutoff)
            if not ids:
                break
            if ids == previous:
                raise ValueError('Retention deletion did not advance')
            total += len(ids)
            if not apply:
                break
            for event_id in ids:
                api(base + '/' + str(event_id), 'DELETE')
            previous = ids
        else:
            raise ValueError('Retention work limit reached; rerun to continue')
    return total


def prune_reports(root, cutoff, apply=False):
    count = 0
    if root.is_symlink():
        raise ValueError('Report folder must not be a symlink')
    for path in root.glob('report-*.md'):
        if path.is_symlink() or not path.is_file():
            continue
        if path.stat().st_mtime < cutoff.timestamp():
            count += 1
            if apply:
                path.unlink()
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=14)
    events = prune(cutoff, args.apply)
    reports = prune_reports(Path.home()/'.local/state/family-lab/reporting', cutoff, args.apply)
    print(json.dumps({'applied': args.apply, 'retention_days': 14,
                      'expired_events': events, 'expired_reports': reports}))


if __name__ == '__main__':
    main()
