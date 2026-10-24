"""Parent policy transport and private reports; no administrator credentials."""
import datetime as dt,json,os,pathlib,re,subprocess,tempfile
from family_identity import helper_config
LIMIT=131072

def request(operation,config=None):
    config=helper_config() if config is None else config
    alias=config.get('policy_alias')
    if not isinstance(alias,str) or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_-]{0,95}',alias):raise ValueError('Screen-time management is not enrolled on this parent desktop')
    raw=json.dumps(operation,allow_nan=False).encode()
    if len(raw)>32768:raise ValueError('Policy request is too large')
    # Bound output on disk before decoding. The remote endpoint authenticates the
    # dedicated policy UID, not the helper label or a submitted identity.
    import resource
    def limit():resource.setrlimit(resource.RLIMIT_FSIZE,(LIMIT,LIMIT))
    with tempfile.TemporaryFile() as output:
        try:
            subprocess.run(['/usr/bin/ssh','-F',config['ssh_config'],'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5','-o','ConnectionAttempts=1','-o','ControlMaster=no','-o','ControlPath=none','-T',alias],input=raw,stdout=output,stderr=subprocess.PIPE,check=True,timeout=20,preexec_fn=limit)
        except subprocess.CalledProcessError as exc:
            detail=(exc.stderr or b'').decode(errors='replace').strip()
            prefix='Family Lab policy: '
            if detail.startswith(prefix):raise ValueError(detail[len(prefix):][:400]) from None
            if any(text in detail.lower() for text in ('no route to host','network is unreachable','connection timed out','operation timed out')):
                raise ValueError('Child PC is unreachable. Wake it if asleep and check that both PCs are on the home network, then click Retry connection or Refresh. Any recent change is unconfirmed.') from None
            if 'connection refused' in detail.lower():
                raise ValueError('Child PC refused the connection. Check its SSH service, then retry. Any recent change is unconfirmed.') from None
            if 'permission denied' in detail.lower():
                raise ValueError('The policy connection was not authorized. Check the enrolled parent key and SSH agent, then retry.') from None
            raise ValueError('Could not reach the policy service. Check the child PC and enrolled connection, then retry. Any recent change is unconfirmed.') from None
        output.seek(0);result=json.load(output)
    if not isinstance(result,dict):raise ValueError('Invalid policy response')
    if 'error' in result:raise ValueError(str(result['error'])[:500])
    return result

def report(summary,peer,home=None):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',peer):raise ValueError('Invalid learner ID')
    def clean(value):return str(value).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('|','&#124;').replace('`','&#96;').replace('[','&#91;').replace(']','&#93;').replace('\n',' ')
    lines=['# Family screen-time report','','Generated: '+dt.datetime.now(dt.timezone.utc).isoformat(),'',clean(summary['coverage'])+'.','Timezone: '+clean(summary['timezone'])+'.','','No app, website, screenshot or keystroke history is collected by this report.','','| Day | Logged-in minutes |','| --- | ---: |']
    observed=False
    for day,rows in sorted(summary['days'].items()):
        if peer in rows:observed=True;lines.append('| '+clean(day)+f' | {rows[peer]/60:.1f} |')
    if not observed:lines.append('| No observations | Unknown |')
    folder=(pathlib.Path.home() if home is None else pathlib.Path(home))/'.local/state/family-help/reports';folder.mkdir(mode=0o700,parents=True,exist_ok=True)
    if folder.is_symlink() or folder.stat().st_uid!=os.getuid() or folder.stat().st_mode&0o077:raise ValueError('Reports need a private parent-owned directory')
    fd,name=tempfile.mkstemp(prefix=peer+'-',suffix='.md',dir=folder)
    with os.fdopen(fd,'w') as output:output.write('\n'.join(lines)+'\n')
    return pathlib.Path(name)

def activity_report(peer, home=None):
    """Use the separately enrolled report role, never the parent-policy key."""
    home = pathlib.Path.home() if home is None else pathlib.Path(home)
    if not isinstance(peer,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',peer):
        raise ValueError('Invalid learner report identity')
    config = home/'.config/family-lab/config.json'
    if not config.is_file() or not json.loads(config.read_text()).get('reporting',{}).get('report_aliases',{}).get(peer):
        raise ValueError('Activity reporting is not enrolled yet. Set up ActivityWatch on the learner and a separate report-only SSH key on this parent PC.')
    executable = home/'.local/bin/family-lab-report'
    if not executable.is_file():raise ValueError('Install the optional Family Lab reporting adapter first')
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        import resource
        def limits():resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024*1024,2*1024*1024))
        result=subprocess.run(['/usr/bin/python3',str(executable),'request',peer,today,today],stdout=output,stderr=errors,timeout=30,preexec_fn=limits)
        if result.returncode:
            raise ValueError('Activity report unavailable. Check the separate reporting enrollment, learner connection and ActivityWatch watchers. No empty report was fabricated.')
        output.seek(0);value=output.read(4097)
    if len(value)>4096:raise ValueError('Invalid activity report path')
    path=pathlib.Path(value.decode().strip())
    if path.parent.resolve()!=(home/'.local/state/family-lab/reporting').resolve() or path.suffix!='.md' or not path.is_file():
        raise ValueError('Activity report was not saved in the private reporting directory')
    return path

def open_content_filter(home=None):
    """Explicit user action opens upstream management; never handles its password."""
    from urllib.parse import urlsplit
    home=pathlib.Path.home() if home is None else pathlib.Path(home)
    config=home/'.config/family-lab/config.json'
    if not config.is_file():raise ValueError('Optional content filtering has not been configured on this parent PC')
    backend=json.loads(config.read_text()).get('integrations',{}).get('adguard_home',{})
    if backend.get('enabled') is not True or backend.get('provider')!='adguard-home':
        raise ValueError('Optional AdGuard Home connection is disabled')
    url=backend.get('management_url','');parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Configure a verified HTTPS AdGuard Home URL without embedded credentials')
    subprocess.run(['xdg-open',url],check=True,timeout=10)
    return 'Opened AdGuard Home management. This does not confirm that client DNS or filtering is active.'

def validate_card(data):
    if isinstance(data,dict) and 'policy_help' in data:
        if set(data)!={'id','time','message','topic','policy_help'} or data['topic']!='time-help' or not re.fullmatch('[a-f0-9]{32}',str(data['id'])) or not isinstance(data['policy_help'],dict) or set(data['policy_help'])!={'peer'} or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',str(data['policy_help']['peer'])):raise ValueError('Invalid time-help card')
        if type(data['time']) not in (int,float) or not 0<=dt.datetime.now(dt.timezone.utc).timestamp()-data['time']<=900 or data['message']!='Please help with bedtime or screen-time settings':raise ValueError('Invalid time-help message')
        return data
    if not isinstance(data,dict) or set(data)!={'id','time','message','topic','break_request'} or data['topic']!='break':raise ValueError('Invalid break card')
    if not re.fullmatch('[a-f0-9]{32}',str(data['id'])) or type(data['time']) not in (int,float) or not 0<=dt.datetime.now(dt.timezone.utc).timestamp()-data['time']<=900:raise ValueError('Expired break card')
    if not isinstance(data['message'],str) or not 1<=len(data['message'])<=300 or not data['message'].isprintable():raise ValueError('Invalid break message')
    item=data['break_request']
    if not isinstance(item,dict) or set(item)!={'peer','episode','revision','change','minutes'} or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',str(item['peer'])) or not re.fullmatch('[a-f0-9]{32}',str(item['episode'])):raise ValueError('Invalid break identity')
    if type(item['revision']) is not int or item['revision']<0 or type(item['minutes']) is not int or not 0<=item['minutes']<=120 or item['change'] not in ('skip','shorten','extend'):raise ValueError('Invalid break change')
    if (item['change']=='skip')!=(item['minutes']==0):raise ValueError('Invalid break duration')
    return data

def pending_cards(config=None):
    result=request({'op':'break-pending'},config)
    items=result['requests']
    if not isinstance(items,list) or len(items)>32:raise ValueError('Oversized pending break list')
    cards=[]
    for item in items:
        change='Skip this break' if item['change']=='skip' else item['change'].capitalize()+' this break by '+str(item['minutes'])+' minutes'
        cards.append(validate_card({'id':item['id'],'time':item['created'],'message':change,'topic':'break','break_request':{key:item[key] for key in ('peer','episode','revision','change','minutes')}}))
    help_items=result.get('help_requests',[])
    if not isinstance(help_items,list) or len(help_items)>32:raise ValueError('Oversized time-help list')
    for item in help_items:cards.append(validate_card({'id':item['id'],'time':item['created'],'message':'Please help with bedtime or screen-time settings','topic':'time-help','policy_help':{'peer':item['peer']}}))
    return cards
