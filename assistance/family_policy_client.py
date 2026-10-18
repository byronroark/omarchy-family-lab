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
        subprocess.run(['/usr/bin/ssh','-F',config['ssh_config'],'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5','-o','ConnectionAttempts=1','-o','ControlMaster=no','-o','ControlPath=none','-T',alias],input=raw,stdout=output,stderr=subprocess.PIPE,check=True,timeout=20,preexec_fn=limit)
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
