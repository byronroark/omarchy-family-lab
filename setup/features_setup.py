"""Optional integrations. Plans by default; no package, DNS or router changes."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]


def private_write(path, text):
    path = Path(path)
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError('Use a real private path, not a symlink')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            output.write(text)
            output.flush(); os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def adguard_compose(image, bind):
    if not re.fullmatch(r'adguard/adguardhome@sha256:[0-9a-f]{64}', image):
        raise ValueError('Choose the official AdGuard Home image pinned to a reviewed sha256 digest')
    address = ipaddress.ip_address(bind)
    if address.version != 4 or not address.is_private or address.is_loopback or address.is_unspecified or address.is_multicast:
        raise ValueError('Select the dedicated host LAN IPv4 address')
    # JSON is valid YAML and avoids shell/YAML interpolation of user input.
    return {'services': {'adguardhome': {
        'image': image, 'restart': 'unless-stopped',
        'ports': [f'{bind}:53:53/tcp', f'{bind}:53:53/udp', '127.0.0.1:3000:3000/tcp', '127.0.0.1:8080:80/tcp'],
        'volumes': ['./work:/opt/adguardhome/work', './conf:/opt/adguardhome/conf'],
        'security_opt': ['no-new-privileges:true'],
    }}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    config = sub.add_parser('configure', help='Choose optional integrations; --apply stages user files only')
    config.add_argument('--activitywatch', choices=['off', 'on'], default='off')
    config.add_argument('--web-bucket'); config.add_argument('--afk-bucket'); config.add_argument('--window-bucket')
    config.add_argument('--browser-app', action='append', default=[])
    config.add_argument('--acknowledge-raw-activitywatch-storage', action='store_true')
    config.add_argument('--adguard', choices=['off', 'existing'], default='off')
    config.add_argument('--adguard-url')
    config.add_argument('--apply', action='store_true')
    compose = sub.add_parser('adguard-compose', help='Generate a dedicated-host deployment file; never starts Docker')
    compose.add_argument('--image', required=True); compose.add_argument('--dns-bind', required=True)
    compose.add_argument('--output', type=Path, required=True); compose.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    if os.geteuid() == 0:
        raise ValueError('Run feature selection as the intended desktop user, not root')
    if args.command == 'adguard-compose':
        data = adguard_compose(args.image, args.dns_bind)
        if args.output.exists(): raise ValueError('Existing deployment preserved; choose a new output path')
        if ROOT == args.output.resolve() or ROOT in args.output.resolve().parents:
            raise ValueError('Keep private deployment files outside the public checkout')
        if args.apply: private_write(args.output, json.dumps(data, indent=2) + '\n')
        print('Generated private Compose file.' if args.apply else 'Plan only: official digest-pinned image; LAN DNS; loopback management; private persistent volumes.')
        print('Not started. An administrator must check ports 53/3000/8080 and firewall rules, start it on an always-on host, complete the upstream wizard and explicitly configure client DNS. No DHCP, router or resolver changes are made.')
        return
    import runpy
    adapter = runpy.run_path(str(ROOT / 'integrations/family_activitywatch.py'))
    activity = {'enabled': False}
    if args.activitywatch == 'on':
        activity = adapter['settings']({'enabled': True, 'port': 5600, 'web_bucket': args.web_bucket,
            'afk_bucket': args.afk_bucket, 'window_bucket': args.window_bucket, 'browser_apps': args.browser_app,
            'acknowledge_raw_storage': args.acknowledge_raw_activitywatch_storage})
    filtering = {'enabled': False}
    if args.adguard == 'existing':
        url = urllib.parse.urlsplit(args.adguard_url or '')
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError('Use a verified HTTPS AdGuard management URL without credentials or query strings')
        filtering = {'enabled': True, 'provider': 'adguard-home', 'management_url': args.adguard_url}
    print('ActivityWatch reports:', args.activitywatch, '| AdGuard connection:', args.adguard)
    print('Requires upstream ActivityWatch, browser extension, and tested Hyprland window/idle watchers. ActivityWatch may store full URLs/titles locally. Family Lab exports only app IDs/domain estimates. No collection daemon, package install, browser install or DNS change is performed here.')
    if not args.apply:
        print('Plan only. Use --apply after reviewing the raw-data disclosure.'); return
    home = Path.home()
    config_path = home / '.config/family-lab/config.json'
    existing = json.loads(config_path.read_text()) if config_path.exists() else {}
    reporting = existing.setdefault('reporting', {})
    if args.activitywatch == 'on':
        reporting.update(enabled=True, provider='activitywatch', activitywatch=activity)
    elif reporting.get('provider') == 'activitywatch':
        reporting['enabled'] = False; reporting['activitywatch'] = activity
    existing.setdefault('integrations', {})['adguard_home'] = filtering
    target = home / '.local/bin'
    # Install only the separate report executable/adapter. Never overwrite the
    # parent's working controls or enroll a report key automatically.
    for source, name in [(ROOT / 'scripts/family-lab-report', 'family-lab-report'),
                         (ROOT / 'integrations/family_activitywatch.py', 'family_activitywatch.py')]:
        dest = target / name
        if dest.exists() and dest.read_bytes() != source.read_bytes():
            raise ValueError('Existing report executable differs; back it up and review before updating: ' + name)
    for source, name in [(ROOT / 'scripts/family-lab-report', 'family-lab-report'),
                         (ROOT / 'integrations/family_activitywatch.py', 'family_activitywatch.py')]:
        private_write(target / name, source.read_text())
        (target / name).chmod(0o755 if name == 'family-lab-report' else 0o644)
    private_write(config_path, json.dumps(existing, indent=2) + '\n')
    print('Optional features staged for this user. Existing assistance settings and report-helper enrollment preserved. No watcher or filter was activated.')


if __name__ == '__main__':
    try: main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit('Feature setup stopped: ' + str(error))
