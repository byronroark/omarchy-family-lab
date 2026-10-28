"""Forced SSH endpoint restricted to existing app/break approval operations."""
import json,os,re,select,socket,sys,time


def permitted(kind, value):
    if not isinstance(value,dict):return False
    if kind=='apps':
        schema={'poll':{'op'},'prepare':{'op','request'},'status':{'op','id'},'decide':{'op','id','review','digest','decision'}}
    elif kind=='breaks':
        schema={'break-pending':{'op'},'break-status':{'op','id'},'break-decision':{'op','id','decision'}}
    else:return False
    if set(value)!=schema.get(value.get('op')):return False
    for field,size in [('id',32),('review',32),('digest',64)]:
        if field in value and (not isinstance(value[field],str) or not re.fullmatch('[a-f0-9]{'+str(size)+'}',value[field])):return False
    if 'decision' in value and value['decision'] not in ('approve','deny'):return False
    return True


def main():
    if len(sys.argv)!=2 or os.environ.get('SSH_ORIGINAL_COMMAND') or os.isatty(0):raise ValueError('Only restricted approval JSON accepted')
    kind=sys.argv[1];raw=b'';deadline=time.monotonic()+8
    while b'\n' not in raw:
        left=deadline-time.monotonic()
        if left<=0 or not select.select([0],[],[],left)[0]:raise ValueError('Input timeout')
        chunk=os.read(0,min(4096,65537-len(raw)))
        if not chunk:raise ValueError('Incomplete input')
        raw+=chunk
        if len(raw)>65536:raise ValueError('Input too large')
    line,extra=raw.split(b'\n',1)
    if extra:raise ValueError('One operation only')
    value=json.loads(line)
    if not permitted(kind,value):raise ValueError('Operation not permitted by Discord transport')
    path='/run/family-help-approval/control.sock' if kind=='apps' else '/run/family-lab/policy.sock'
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(40);sock.connect(path);sock.sendall(json.dumps(value).encode()+b'\n')
        result=b''
        while not result.endswith(b'\n'):
            chunk=sock.recv(4096)
            if not chunk or len(result)+len(chunk)>65536:raise ValueError('Invalid response')
            result+=chunk
    print(json.dumps(json.loads(result)))


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)[:200]}));sys.exit(1)
