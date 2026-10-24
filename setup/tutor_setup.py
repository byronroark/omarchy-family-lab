"""Connect a parent desktop to an existing managed DeepTutor learner host.

No administrator keys, OAuth tokens, passwords or child work cross machines.
DeepTutor account creation is a separate private administrator phase.
"""
import html
import ipaddress
import json
import os
from pathlib import Path
import pwd
import subprocess
from urllib.request import ProxyHandler, build_opener

CONTAINER = 'family-learning-learner'


def validate(profile):
    config = profile.get('tutor', {'enabled': False})
    if not isinstance(config, dict) or set(config) - {'enabled', 'port', 'parent_login', 'firewall'}:
        raise ValueError('Invalid tutoring enrollment settings')
    if type(config.get('enabled')) is not bool:
        raise ValueError('Tutoring enabled must be a boolean')
    if not config['enabled']:
        return config
    host = ipaddress.ip_address(profile['learner']['host'])
    helper = ipaddress.ip_address(profile.get('helper', profile.get('dad'))['host'])
    if host.version != 4 or helper.version != 4 or not host.is_private or not helper.is_private or host.is_loopback or helper.is_loopback or host.is_unspecified or helper.is_unspecified:
        raise ValueError('Tutoring enrollment requires explicit private LAN IPv4 addresses')
    if type(config.get('port')) is not int or config['port'] != 3785:
        raise ValueError('This managed DeepTutor host uses port 3785')
    name = config.get('parent_login', '')
    import re
    if not isinstance(name, str) or not re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}', name) or name == profile['learner']['login']:
        raise ValueError('Choose a separate plain DeepTutor parent login')
    if type(config.get('firewall', True)) is not bool:
        raise ValueError('Tutoring firewall selection must be boolean')
    return config


def address(profile):
    config = validate(profile)
    return f"http://{profile['learner']['host']}:{config['port']}"


def helper_files(profile, home=None):
    config = validate(profile)
    if not config['enabled']:
        return {}
    url = address(profile)
    result = {}
    for suffix, title, route in [('Learning', 'Family Learning', '/family-learning'), ('Authoring', 'DeepTutor parent dashboard', '/chat'), ('AI', 'Connect my tutoring AI', '/settings/connections')]:
        result[f'.local/share/applications/org.familylab.{suffix}.desktop'] = (
            f'[Desktop Entry]\nType=Application\nName={title}\nExec=xdg-open {url}{route}\nIcon=applications-education\nTerminal=false\nCategories=Education;\n'.encode(), 0o644, False)
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Family Manager setup</title>
<style>body{{font:18px system-ui;max-width:760px;margin:3rem auto;padding:1rem;line-height:1.6;color:#eee;background:#1a1918}}a{{color:#9acbfa}}li{{margin:1rem 0}}</style>
<h1>Your Family Manager setup</h1><ol>
<li>The technical parent installs your enrollment bundle on the child's PC. Your approval-only SSH key cannot open an administrator shell.</li>
<li><a href="{url}/family-learning">Open Family Learning</a> and sign in as <strong>{html.escape(config['parent_login'])}</strong> using your separate application password. The administrator creates this account privately; the installer never copies another parent's account or password.</li>
<li><a href="{url}/settings/connections">Connect your own ChatGPT account</a> privately in Providers. Complete the sign-in yourself. If the callback page cannot load, paste its entire address into DeepTutor's callback field, never into chat. No callback tunnel is configured by this enrollment.</li>
<li>Select your model, generate a course draft, review it, check the reference programs and publish privately. Assign it to the child only when ready.</li>
<li>Test an app request: deny one new request, then approve a separate reviewed request. If controls are selected, test a break request too.</li></ol>
<p>DeepTutor runs on the child's PC, so it must be awake. Your AI account and courses remain separate from the other parent's. The child cannot access provider settings or free-form AI chat.</p></html>'''
    result['.local/share/family-help/parent-onboarding.html'] = (page.encode(), 0o600, False)
    home = Path.home() if home is None else home
    result['.local/share/applications/org.familylab.Onboarding.desktop'] = (
        ('[Desktop Entry]\nType=Application\nName=Family Manager setup\nExec=xdg-open "'+str(home / '.local/share/family-help/parent-onboarding.html')+'"\nIcon=help-browser\nTerminal=false\nCategories=Education;\n').encode(),0o644,False)

    result['.config/family-help/tutor.json'] = (json.dumps({'url': url, 'parent_login': config['parent_login'], 'provider_setup': 'complete privately in the browser'}).encode(), 0o600, False)
    return result


def inspect_host(profile, run=subprocess.run):
    config = validate(profile)
    if not config['enabled']:
        return None
    result = run(['docker', 'inspect', CONTAINER], check=True, capture_output=True, text=True)
    item = json.loads(result.stdout)[0]
    if item['Config'].get('Labels', {}).get('family-learning.owner') != 'learner-host' or not item['State']['Running']:
        raise ValueError('A running managed DeepTutor host is required; no existing data will be replaced')
    if item['HostConfig']['PortBindings'] or any(m['Destination'] == '/var/run/docker.sock' for m in item['Mounts']):
        raise ValueError('Unexpected DeepTutor container exposure')
    env = dict(value.split('=', 1) for value in item['Config']['Env'] if '=' in value)
    if any(env.get(key) != '1' for key in ['FAMILY_LEARNING_ENABLED', 'FAMILY_LEARNING_LOCAL_ONLY', 'FAMILY_LEARNER_HOST']):
        raise ValueError('DeepTutor learner restrictions are not enabled')
    if env.get('FAMILY_PARENT_CLOUD') != '1':
        raise ValueError('The reviewed parent dashboard/OpenAI host setup is required before personal AI enrollment')
    if address(profile) not in env.get('FAMILY_LEARNING_ORIGIN', '').split(','):
        raise ValueError('DeepTutor LAN origin is not configured; run the reviewed host LAN setup first')
    mounts = {m['Destination']: m['Source'] for m in item['Mounts']}
    if mounts.get('/app/data') != '/var/lib/family-learning/data':
        raise ValueError('Unexpected DeepTutor data directory')
    return item


def check_reachable(profile):
    with build_opener(ProxyHandler({})).open(address(profile) + '/api/auth/status', timeout=8) as response:
        data = json.load(response)
    if data.get('enabled') is not True:
        raise ValueError('DeepTutor authentication is not enabled')
    return data


def install(api, profile, args):
    config = validate(profile)
    if not config['enabled']:
        return
    if os.geteuid() != 0:
        raise ValueError('The technical administrator enrolls the tutoring account on the child host')
    inspect_host(profile)
    check_reachable(profile)
    user = pwd.getpwnam('familylearn')
    # Inspect only safe account metadata; no hashes, tokens or student records.
    base = ['docker', 'exec', '--user', f'{user.pw_uid}:{user.pw_gid}', CONTAINER, 'python', '-c']
    query = "import json;from deeptutor.services.auth import list_users;print(json.dumps([{'username':u['username'],'role':u['role']} for u in list_users()]))"
    accounts = json.loads(subprocess.check_output(base + [query], text=True))
    existing = next((u for u in accounts if u['username'] == config['parent_login']), None)
    if existing and existing['role'] != 'admin':
        raise ValueError('Existing non-parent account preserved; no automatic role promotion')
    # A narrow incoming rule is sufficient for this parent's existing SSH transport
    # and direct browser connection. Never enable/disable the firewall or flush it.
    if config.get('firewall', True):
        status = subprocess.check_output(['ufw', 'status'], text=True)
        if 'Status: active' not in status:
            raise ValueError('Expected an active UFW firewall; configure it deliberately before enrollment')
        rows = json.loads(subprocess.check_output(['ip', '-j', '-4', 'addr', 'show'], text=True))
        matches = [row['ifname'] for row in rows if any(a.get('local') == profile['learner']['host'] for a in row.get('addr_info', []))]
        if len(matches) != 1:
            raise ValueError('Learner LAN address must match exactly one local interface')
        helper = api['selected_helper'](profile)
        for port in [profile['learner']['port'], config['port']]:
            api['run'](['ufw', 'allow', 'in', 'on', matches[0], 'proto', 'tcp', 'from', helper['host'], 'to', profile['learner']['host'], 'port', str(port), 'comment', 'Family Manager parent enrollment'])
    if not existing:
        code = '''import getpass,sys
from deeptutor.services.auth import add_user,list_users
name=sys.argv[1]
if any(u['username']==name for u in list_users()):raise SystemExit('Account appeared during setup; retry to inspect it')
while True:
 value=getpass.getpass('New DeepTutor parent password: ')
 if not 8<=len(value.encode())<=72:print('Use 8–72 bytes');continue
 if getpass.getpass('Confirm password: ')==value:break
 print('Passwords did not match')
add_user(name,value,role='admin')
print('DeepTutor parent account created. No AI provider is connected yet.')'''
        subprocess.run(['docker', 'exec', '-it', '--user', f'{user.pw_uid}:{user.pw_gid}', CONTAINER, 'python', '-c', code, config['parent_login']], check=True)
    print('DeepTutor parent ready:', config['parent_login'], address(profile))
    print('Existing accounts, coursework and other parents were preserved. Complete personal AI sign-in privately from the new parent desktop.')


def verify(profile):
    config = validate(profile)
    check_reachable(profile)
    if os.geteuid() == 0:
        inspect_host(profile)
        user = pwd.getpwnam('familylearn')
        code = "import json;from deeptutor.services.auth import list_users;print(json.dumps([{'username':u['username'],'role':u['role']} for u in list_users()]))"
        accounts = json.loads(subprocess.check_output(['docker','exec','--user',f'{user.pw_uid}:{user.pw_gid}',CONTAINER,'python','-c',code],text=True))
        if not any(u['username'] == config['parent_login'] and u['role'] == 'admin' for u in accounts):
            raise ValueError('Configured tutoring parent account is not enrolled')
    print('DeepTutor host reachable with authentication enabled. Parent sign-in, personal OAuth and request-card acceptance still require the documented desktop checks.')
