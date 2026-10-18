"""Bounded delegated approval protocol and root-owned job state.

No SSH command strings, shell evaluation, administrator identity, or caller paths.
"""
import contextlib,fcntl,hashlib,json,os,pathlib,re,socket,stat,struct,time,uuid
from family_software import validate_request
MAX_WIRE=65536
ID=re.compile(r'[a-f0-9]{32}')
DIGEST=re.compile(r'[a-f0-9]{64}')
PACKAGE=re.compile(r'[a-z0-9][a-z0-9._+-]{0,63}/[a-z0-9@_+][a-z0-9@._+-]{0,127}')
PINNED=re.compile(r'[a-z0-9][a-z0-9._+-]{0,63}/[a-z0-9@_+][a-z0-9@._+-]{0,127}=[A-Za-z0-9:.+_~\-]{1,128}')
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
def identifier(value):
    if not isinstance(value,str) or not ID.fullmatch(value):raise ValueError('Invalid request/review ID')
    return value

def read_message(stream,limit=MAX_WIRE):
    data=b''
    while b'\n' not in data:
        chunk=stream.recv(min(4096,limit+1-len(data)))
        if not chunk:raise ValueError('Incomplete approval message')
        data+=chunk
        if len(data)>limit:raise ValueError('Approval message too large')
    line,extra=data.split(b'\n',1)
    if extra:raise ValueError('Only one approval operation per connection')
    value=json.loads(line)
    if not isinstance(value,dict):raise ValueError('Approval operation must be an object')
    return value

def send_message(stream,value):
    data=json.dumps(value,separators=(',',':'),ensure_ascii=True).encode()+b'\n'
    if len(data)>MAX_WIRE:raise ValueError('Approval reply too large')
    stream.sendall(data)

def peer_uid(connection):return struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))[1]

def trusted(path,owner=0):
    for item in (path,*path.parents):
        st=item.lstat()
        if stat.S_ISLNK(st.st_mode) or st.st_uid!=owner or st.st_mode&0o022:raise ValueError('Unsafe approval state/configuration path')

def write_json(path,value,mode=0o600):
    temp=path.with_name('.'+path.name+'.'+uuid.uuid4().hex)
    fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    try:
        with os.fdopen(fd,'w') as file:
            json.dump(value,file,ensure_ascii=True);file.flush();os.fsync(file.fileno())
        os.chmod(temp,mode);os.replace(temp,path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:temp.unlink(missing_ok=True)

class Broker:
    """Authorization from peer UID, exact reviewed plans and one-shot decisions.

    Planner and executor are injected so isolated tests never execute packages.
    The production entry point supplies only root-reviewed implementations.
    """
    def __init__(self,base,principals,planner,executor,clock=time.time,poller=lambda:{},identity_guard=lambda uid,entry:None):
        self.identity_guard=identity_guard;self.poller=poller
        self.base=pathlib.Path(base);self.principals=principals;self.planner=planner;self.executor=executor;self.clock=clock
        for name,mode in [('audit',0o700),('results',0o755),('approval-reviews',0o700),('approval-jobs',0o700)]:
            folder=self.base/name;folder.mkdir(mode=mode,parents=True,exist_ok=True)
    def principal(self,uid):
        entry=self.principals.get(str(uid))
        if not isinstance(entry,dict) or entry.get('enabled') is not True:raise ValueError('This account is not an enrolled approval-only parent')
        self.identity_guard(uid,entry)
        return entry
    @contextlib.contextmanager
    def lock(self):
        with (self.base/'audit/action.lock').open('a') as file:
            fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB)
            yield
    def receipt(self,identifier_):return self.base/'audit'/(identifier(identifier_)+'.json')
    def record(self,request,status,principal,code=None):
        value={'id':request['id'],'status':status,'returncode':code,'time':self.clock()}
        write_json(self.receipt(request['id']),dict(value,request=request,approver=principal))
        write_json(self.base/'results'/(request['id']+'.json'),value,0o644)
    def operation(self,uid,value):
        principal=self.principal(uid)
        if value=={'op':'poll'}:return {'ok':True,'request':self.poller()}
        if value.get('op')=='prepare' and set(value)=={'op','request'}:
            request=validate_request(value['request'])
            if self.receipt(request['id']).exists():
                current=json.loads(self.receipt(request['id']).read_text())
                return {'ok':True,'id':request['id'],'already_decided':True,'status':current['status']}
            plan=self.planner(request,principal)
            review={'id':request['id'],'review':uuid.uuid4().hex,'request':request,'plan':plan,'uid':uid,'expires':min(request['time']+900,self.clock()+300)}
            review['digest']=digest({'request':request,'plan':plan})
            folder=self.base/'approval-reviews'/str(uid);folder.mkdir(mode=0o700,exist_ok=True)
            write_json(folder/(request['id']+'.json'),review)
            return {'ok':True,'id':request['id'],'review':review['review'],'digest':review['digest'],'expires':review['expires'],'plan':plan}
        if value.get('op')=='decide' and set(value)=={'op','id','review','digest','decision'}:
            request_id=identifier(value['id']);identifier(value['review'])
            if not isinstance(value['digest'],str) or not DIGEST.fullmatch(value['digest']) or value['decision'] not in ('approve','deny'):raise ValueError('Invalid approval decision')
            review=json.loads((self.base/'approval-reviews'/str(uid)/(request_id+'.json')).read_text())
            if review['uid']!=uid or review['review']!=value['review'] or review['digest']!=value['digest'] or review['expires']<=self.clock():raise ValueError('Approval review changed or expired; reopen the request')
            validate_request(review['request'])
            with self.lock():
                if self.receipt(request_id).exists():raise ValueError('This request already has a decision; ask again')
                if value['decision']=='deny':self.record(review['request'],'denied',principal['id']);return {'ok':True,'status':'denied'}
                if not review['plan'].get('supported'):raise ValueError('This action needs the technical helper; it cannot be approved here')
                if digest(self.planner(review['request'],principal))!=digest(review['plan']):raise ValueError('The package plan changed; review it again')
                # Receipt first: interruption between these writes cannot replay approval.
                self.record(review['request'],'queued',principal['id'])
                write_json(self.base/'approval-jobs'/(request_id+'.json'),dict(review,principal=principal['id']))
                return {'ok':True,'status':'queued'}
        if value.get('op')=='status' and set(value)=={'op','id'}:
            path=self.receipt(identifier(value['id']))
            if not path.exists():return {'ok':True,'status':'pending'}
            result=json.loads(path.read_text())
            return {'ok':True,**{key:result[key] for key in ('id','status','returncode')}}
        raise ValueError('Unknown or malformed approval operation')
    def recover(self):
        # Never replay a job that may already have changed the system.
        for path in (self.base/'audit').glob('*.json'):
            if not ID.fullmatch(path.stem):continue
            record=json.loads(path.read_text())
            if 'approver' not in record:continue
            if record.get('status')=='running':self.record(record['request'],'interrupted',record['approver'],1)
            elif record.get('status')=='queued' and not (self.base/'approval-jobs'/path.name).exists():self.record(record['request'],'interrupted',record['approver'],1)
    def run_next(self):
        for path in sorted((self.base/'approval-jobs').glob('*.json')):
            if not ID.fullmatch(path.stem):continue
            with self.lock():
                job=json.loads(path.read_text());receipt=self.receipt(path.stem)
                if not receipt.exists() or json.loads(receipt.read_text()).get('status')!='queued':continue
                request=job['request'];principal={'id':job['principal']}
                try:
                    principal=self.principal(job['uid'])
                    if principal['id']!=job['principal']:raise ValueError('Approver identity changed')
                    validate_request(request)
                    if job['expires']<=self.clock():raise ValueError('Queued approval expired')
                    if digest(self.planner(request,principal))!=digest(job['plan']):raise ValueError('Approved package plan changed')
                    self.record(request,'running',principal['id'])
                    code=self.executor(request,job['plan'])
                    self.record(request,'completed' if code==0 else 'failed',principal['id'],code)
                except Exception:
                    self.record(request,'failed',principal['id'],1)
                return True
        return False

def serve_connection(connection,broker):
    connection.settimeout(10)
    try:
        # Authorize BEFORE parsing caller data or exposing any status.
        uid=peer_uid(connection);broker.principal(uid)
        result=broker.operation(uid,read_message(connection))
    except BlockingIOError:
        result={'ok':False,'error':'Another family maintenance action is running. Wait for it to finish; this decision was not accepted.'}
    except (OSError,ValueError,KeyError,TypeError,RecursionError) as exc:
        result={'ok':False,'error':str(exc)[:300]}
    send_message(connection,result)
