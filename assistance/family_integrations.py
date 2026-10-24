"""Parent integration controls. Collection uses report SSH; filtering is per-client."""
import base64
import copy
import json
import ipaddress
import os
from pathlib import Path
import stat
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Filter redirects are not allowed')


class AdGuard:
    def __init__(self, peer, home=None):
        home = Path.home() if home is None else Path(home)
        path = home / '.config/family-lab/adguard-control.json'
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd) as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError('AdGuard control credentials must be a private parent-owned 0600 file')
            raw = source.read(16385)
        if len(raw) > 16384: raise ValueError('Oversized AdGuard enrollment')
        value = json.loads(raw)
        if set(value) != {'url','username','password','peer','client_name','client_ids'} or value['peer'] != peer:
            raise ValueError('AdGuard control is not enrolled for this learner')
        parsed = urllib.parse.urlsplit(value['url'])
        if parsed.scheme != 'https' or not parsed.hostname or parsed.path not in ('','/') or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Use a verified HTTPS AdGuard origin without embedded credentials')
        for key in ('username','password','client_name'):
            if not isinstance(value[key], str) or not 1 <= len(value[key]) <= 1024 or '\n' in value[key] or '\r' in value[key]:
                raise ValueError('Invalid AdGuard enrollment field')
        if ':' in value['username']: raise ValueError('Invalid AdGuard username')
        ids = value['client_ids']
        if not isinstance(ids,list) or not 1 <= len(ids) <= 8 or any(not isinstance(x,str) or not 1 <= len(x) <= 128 for x in ids) or len(set(ids)) != len(ids):
            raise ValueError('Enroll exact device identifiers, not an entire client group')
        # No subnet enrollment: a toggle must not change filtering for a network.
        if any('/' in value or value in ('0.0.0.0','::') for value in ids):
            raise ValueError('Subnet-wide AdGuard clients cannot be controlled here')
        import re
        for identifier in ids:
            try:
                address=ipaddress.ip_address(identifier)
                if address.is_unspecified or address.is_multicast or address.is_loopback:
                    raise ValueError('Use device-specific AdGuard identifiers')
            except ValueError:
                if not (re.fullmatch(r'[A-Za-z0-9_-]{1,64}',identifier) or re.fullmatch(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}',identifier)):
                    raise ValueError('Use exact device IPs, MAC addresses or client IDs; no wildcards')
        self.config = value

    def api(self, endpoint, data=None):
        if endpoint not in ('clients','status','clients/update'):
            raise ValueError('Unsupported AdGuard action')
        secret = (self.config['username'] + ':' + self.config['password']).encode()
        headers = {'Authorization':'Basic ' + base64.b64encode(secret).decode(), 'Content-Type':'application/json'}
        request = urllib.request.Request(self.config['url'].rstrip('/') + '/control/' + endpoint,
            data=json.dumps(data).encode() if data is not None else None, headers=headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        try:
            with opener.open(request, timeout=5) as response: raw = response.read(1024*1024+1)
        except Exception:
            raise ValueError('Could not confirm AdGuard response; check its connection and private credentials') from None
        if len(raw)>1024*1024: raise ValueError('Oversized AdGuard response')
        return json.loads(raw) if raw.strip() else {}

    def client(self):
        response=self.api('clients')
        rows=response.get('clients')
        if not isinstance(rows,list):raise ValueError('Unsupported AdGuard clients response')
        rows=[row for row in rows if row.get('name')==self.config['client_name']]
        if len(rows)!=1 or sorted(rows[0].get('ids',[]))!=sorted(self.config['client_ids']):
            raise ValueError('AdGuard client identity changed; review enrollment before acting')
        row=rows[0]
        if row.get('use_global_settings') is not False:
            raise ValueError('Configure explicit per-client AdGuard settings first; inherited global settings are not changed here')
        for key in ('filtering_enabled','parental_enabled','safebrowsing_enabled'):
            if type(row.get(key)) is not bool:raise ValueError('Unsupported AdGuard per-client settings')
        return row

    def status(self):
        row=self.client();server=self.api('status')
        switches=[row[key] for key in ('filtering_enabled','parental_enabled','safebrowsing_enabled')]
        if type(server.get('protection_enabled')) is not bool or type(server.get('running')) is not bool:
            raise ValueError('Unsupported AdGuard server status')
        return {'ready':True,'enabled':all(switches) and server['protection_enabled'] and server['running'],
                'client_enabled':all(switches),'mixed':any(switches) and not all(switches),
                'server_enabled':server['protection_enabled'] and server['running'],
                'message':'Per-client blocklists, adult-domain and malware settings; DNS routing/coverage still needs verification. SafeSearch is managed separately.'}

    def set_enabled(self, enabled):
        if type(enabled) is not bool:raise ValueError('Expected boolean filter choice')
        row=self.client();server=self.api('status')
        if enabled and (server.get('protection_enabled') is not True or server.get('running') is not True):
            raise ValueError('AdGuard global protection is paused; restore it in upstream management first')
        if self.client()!=row:
            raise ValueError('AdGuard client settings changed; refresh and review before applying')
        changed=copy.deepcopy(row)
        for key in ('filtering_enabled','parental_enabled','safebrowsing_enabled'):changed[key]=enabled
        self.api('clients/update', {'name':self.config['client_name'],'data':changed})
        result=self.status()
        if result['client_enabled'] != enabled or result['mixed'] or (enabled and not result['enabled']):
            raise ValueError('AdGuard did not confirm the requested client settings; refresh before retrying')
        return result


def open_panel(parent, peer, collection):
    """Separate window; backend errors never discard the parent's schedule edits."""
    import threading
    import gi
    gi.require_version('Gtk','4.0')
    from gi.repository import Gtk, GLib
    window=Gtk.Window(title='Family Manager - integrations',transient_for=parent,default_width=560,default_height=640)
    window.add_css_class('family-time')
    box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin_top=20,margin_bottom=20,margin_start=20,margin_end=20)
    scroll=Gtk.ScrolledWindow(vexpand=True);scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
    scroll.set_child(box);window.set_child(scroll)
    def label(text):
        node=Gtk.Label(label=text,xalign=0,wrap=True);box.append(node);return node
    label('OPTIONAL INTEGRATIONS').add_css_class('heading')
    label('ActivityWatch collection on the learner PC')
    activity=label('Checking setup…')
    ack=Gtk.CheckButton(label='I understand ActivityWatch may store full URLs and titles locally.')
    box.append(ack)
    label('Stopping the supervised target does not delete history. Disable the browser extension too if you do not want it to retain pending events while the server is stopped.')
    activity_row=Gtk.Box(spacing=8,homogeneous=True);box.append(activity_row)
    label('AdGuard Home - selected learner only')
    filtering=label('Checking setup…')
    filter_row=Gtk.Box(spacing=8,homogeneous=True);box.append(filter_row)
    feedback=label('No changes made. First-time installation/enrollment requires an administrator.')
    feedback.add_css_class('feedback')
    buttons=[];state={'busy':False,'collection':False,'filter':False}
    def update():
        start.set_sensitive(not state['busy'] and state['collection'] and ack.get_active())
        stop.set_sensitive(not state['busy'] and state['collection'])
        for button in (enable,disable):button.set_sensitive(not state['busy'] and state['filter'])
        refresh.set_sensitive(not state['busy'])
    def task(work,done):
        if state['busy']:return
        state['busy']=True;feedback.set_text('Checking with the backend…');update()
        def worker():
            try:value,error=work(),None
            except Exception as exc:value,error=None,str(exc)[:350]
            def finish():
                state['busy']=False
                if error:feedback.set_text('Not confirmed: '+error)
                else:done(value)
                update();return False
            GLib.idle_add(finish)
        threading.Thread(target=worker,daemon=True).start()
    def collect_action(enabled):
        task(lambda:collection(peer,{'op':'collection-set','enabled':enabled,'acknowledge_raw_storage':ack.get_active()}),
             lambda value:show_activity(value))
    def show_activity(value):
        state['collection']=value.get('ready') is True
        activity.set_text('Collection service: '+value.get('state','unknown'))
        feedback.set_text(value.get('message','Backend confirmed'))
    def filter_action(enabled):
        task(lambda:AdGuard(peer).set_enabled(enabled),show_filter)
    def show_filter(value):
        state['filter']=value.get('ready') is True
        text='Enabled' if value.get('enabled') else 'Mixed client settings' if value.get('mixed') else 'Paused globally' if not value.get('server_enabled') else 'Disabled'
        filtering.set_text('Client domain protections: '+text)
        feedback.set_text(value.get('message','Backend confirmed'))
    def button(text,callback,row):
        node=Gtk.Button(label=text);node.connect('clicked',lambda *_:callback());row.append(node);return node
    start=button('Start collection',lambda:collect_action(True),activity_row)
    stop=button('Stop collection',lambda:collect_action(False),activity_row)
    enable=button('Enable filtering',lambda:filter_action(True),filter_row)
    disable=button('Disable filtering',lambda:filter_action(False),filter_row)
    def read_status():
        result={}
        for key,work in [('collection',lambda:collection(peer,{'op':'collection-status'})),('filter',lambda:AdGuard(peer).status())]:
            try:result[key]=work()
            except Exception as exc:result[key]={'ready':False,'error':str(exc)[:250]}
        return result
    def display(result):
        value=result['collection'];state['collection']=value.get('ready') is True
        if state['collection']:show_activity(value)
        else:activity.set_text('Collection not ready: '+value.get('error',value.get('message','setup required')))
        value=result['filter'];state['filter']=value.get('ready') is True
        if state['filter']:show_filter(value)
        else:filtering.set_text('Filter not ready: '+value.get('error','setup required'))
        feedback.set_text('Status refreshed. Unavailable controls stay disabled until setup is complete.')
    tools=Gtk.Box(spacing=8,homogeneous=True);box.append(tools)
    refresh=button('Refresh status',lambda:task(read_status,display),tools)
    button('Close',window.close,tools)
    ack.connect('toggled',lambda *_:update())
    window.present();task(read_status,display)
    return window
