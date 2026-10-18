"""Typed software requests. No commands, paths, flags, or AUR builds are accepted."""
import json,math,os,pathlib,re,stat,time
PACKAGE=r'[a-z0-9][a-z0-9._+-]{0,63}/[a-z0-9@_+][a-z0-9@._+-]{0,127}'
def validate_software(value):
    if isinstance(value,dict) and value.get('action')=='menu':
        if set(value)!={'action','packages','menu'} or value['packages']!=[]:raise ValueError('Invalid menu request')
        from family_menu import entry
        entry(value['menu']);return value
    if not isinstance(value,dict) or set(value)!={'action','packages'}:raise ValueError('Invalid software request')
    action=value['action'];packages=value['packages']
    if action not in ('install','update') or not isinstance(packages,list):raise ValueError('Invalid operation')
    if action=='update' and packages:raise ValueError('Updates take no package arguments')
    if action=='install' and not 1<=len(packages)<=5:raise ValueError('Select one to five repository packages')
    if any(not isinstance(x,str) or not re.fullmatch(PACKAGE,x) for x in packages) or len(set(packages))!=len(packages):raise ValueError('Use unique repository/package names; no files or options')
    return value
def validate_request(value):
    if not isinstance(value,dict) or set(value)!={'id','time','message','topic','software'}:raise ValueError('Invalid approval fields')
    if not isinstance(value['id'],str) or not re.fullmatch('[a-f0-9]{32}',value['id']):raise ValueError('Invalid ID')
    if type(value['time']) not in (int,float) or not math.isfinite(value['time']) or not 0<=time.time()-value['time']<=900:raise ValueError('Software request expired; ask again')
    if value['topic']!='admin' or not isinstance(value['message'],str) or not 1<=len(value['message'])<=300 or not all(c.isprintable() for c in value['message']):raise ValueError('Invalid request text')
    validate_software(value['software']);return value
def read_private(path,owner):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        st=os.fstat(stream.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=owner or st.st_mode&0o022:raise ValueError('Unsafe approval snapshot')
        data=stream.read(2049)
    if len(data)>2048:raise ValueError('Oversized approval')
    return validate_request(json.loads(data))
def result_path(identifier):
    if not re.fullmatch('[a-f0-9]{32}',identifier):raise ValueError('Invalid ID')
    return pathlib.Path('/var/lib/family-software/results')/(identifier+'.json')
