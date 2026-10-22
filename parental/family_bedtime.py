"""Bedtime hibernation countdown; no learner-controlled power commands."""
import math
import stat
import subprocess
import uuid


class Bedtime:
    def __init__(self, path, read, write, ready_path):
        self.path, self.read, self.write, self.ready_path = path, read, write, ready_path
        self.rows = read(path) if path.exists() else {}
        if not isinstance(self.rows, dict):
            raise ValueError('Invalid bedtime power state')
        for row in self.rows.values():
            if (not isinstance(row, dict) or set(row) != {'episode', 'boot', 'deadline', 'offset', 'retry', 'error', 'requested'}
                    or not isinstance(row['episode'], str) or not isinstance(row['boot'], str)
                    or type(row['requested']) is not bool or not isinstance(row['error'], str)
                    or any(type(row[k]) not in (int, float) or not math.isfinite(row[k]) for k in ('deadline', 'offset', 'retry'))):
                raise ValueError('Invalid bedtime power timer')
        self.secure = {}

    def ready(self, peer):
        try:
            info = self.ready_path.lstat()
            return (stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022
                    and self.read(self.ready_path) == {'peer': peer, 'resume_verified': True})
        except (OSError, ValueError, TypeError):
            return False

    def sync(self, status, boot, elapsed, monotonic):
        wanted = {p for p, r in status.items() if r['mode'] == 'enforce' and r['blocked']
                  and r['reason'] == 'outside-hours' and r['logged_in'] and self.ready(p)}
        updated = {p: r.copy() for p, r in self.rows.items() if p in wanted}
        offset = elapsed - monotonic
        for peer in wanted:
            row = updated.get(peer)
            if row is None or row['boot'] != boot or offset - row['offset'] > 2:
                updated[peer] = {'episode': uuid.uuid4().hex, 'boot': boot, 'deadline': elapsed + 300,
                                 'offset': offset, 'retry': 0, 'error': '', 'requested': False}
                self.secure.pop(peer, None)
        if updated != self.rows:
            self.write(self.path, updated)
            self.rows = updated
        for peer in set(self.secure) - wanted:
            self.secure.pop(peer, None)

    def view(self, peer, elapsed):
        row = self.rows.get(peer)
        if not row or not self.ready(peer):
            return {'enabled': False, 'remaining_seconds': None, 'episode': None,
                    'error': 'Hibernation awaits a parent-verified sleep and resume test.'}
        return {'enabled': True, 'episode': row['episode'],
                'remaining_seconds': max(0, math.ceil(row['deadline'] - elapsed)),
                'error': row['error'], 'requested': row['requested']}

    def protected(self, peer, elapsed):
        self.secure[peer] = elapsed

    def request(self, peer, episode, elapsed):
        row = self.rows.get(peer)
        if not row or not self.ready(peer) or row['episode'] != episode:
            raise ValueError('Bedtime changed; refresh before hibernating')
        if not 0 <= elapsed - self.secure.get(peer, -1000) <= 10:
            raise ValueError('Protected screen must be confirmed first')
        if elapsed < row['retry']:
            raise ValueError('Hibernation failed; wait before retrying')
        updated = {p: r.copy() for p, r in self.rows.items()}
        updated[peer]['requested'] = True
        self.write(self.path, updated)
        self.rows = updated
        return {'accepted': True}

    def enforce(self, peer, row, elapsed, audit):
        timer = self.rows.get(peer)
        if (not timer or not self.ready(peer) or row['mode'] != 'enforce' or not row['blocked']
                or row['reason'] != 'outside-hours' or not row['logged_in']
                or not 0 <= elapsed - self.secure.get(peer, -1000) <= 10
                or elapsed < timer['retry'] or (elapsed < timer['deadline'] and not timer['requested'])):
            return
        updated = {p: r.copy() for p, r in self.rows.items()}
        updated[peer].update(retry=elapsed + 60, requested=False)
        self.write(self.path, updated)
        self.rows = updated
        audit('service', 'bedtime-hibernate', {'peer': peer})
        try:
            subprocess.run(['/usr/bin/busctl', '--system', 'call', 'org.freedesktop.login1',
                            '/org/freedesktop/login1', 'org.freedesktop.login1.Manager',
                            'Hibernate', 'b', 'false'], check=True, capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            updated[peer]['error'] = 'Could not hibernate. Your work stays protected. Ask a parent or retry shortly.'
            audit('service', 'bedtime-hibernate-failed', {'peer': peer})
        else:
            updated[peer]['error'] = ''
        self.write(self.path, updated)
        self.rows = updated
