import ast,hashlib,json,os,pathlib,re,struct,subprocess,sys,tempfile,time,zlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'assistance'))
from family_help_image import normalize_png,MAX_IMAGE,prune
def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
original=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,2,8,2,0,0,0))+chunk(b'tEXt',b'private-test-metadata\0do not transfer')+chunk(b'IDAT',zlib.compress((b'\0'+b'\x10\x20\x30'*2)*2))+chunk(b'IEND',b'')
clean,info=normalize_png(original)
assert b'private-test-metadata' not in clean
assert info['width']==2 and info['height']==2
assert normalize_png(clean)[0]==clean
bad=[b'<svg/>',b'not png',clean+b'payload',clean[:50],b'x'*(MAX_IMAGE+1)]
header=struct.pack('>IIBBBBB',20000,20000,8,2,0,0,0)
bomb=clean[:16]+header+struct.pack('>I',zlib.crc32(b'IHDR'+header)&0xffffffff)+clean[33:]
bad.append(bomb)
for data in bad:
    try:normalize_png(data)
    except ValueError:pass
    else:raise AssertionError('Bad PNG accepted')
print('PASS: PNG metadata removed; invalid, oversized, truncated, trailing payload and oversized dimensions rejected')
with tempfile.TemporaryDirectory(prefix='family-help-widget-',dir='/tmp') as temp:
    base=pathlib.Path(temp);state=base/'state';drafts=state/'drafts';drafts.mkdir(parents=True)
    conf=base/'child.json';conf.write_text(json.dumps({'uid':os.getuid(),'state':str(state),'socket':str(base/'tmux.sock'),'session':'learning','viewer':'unused'}))
    (base/'family_identity.py').write_bytes((pathlib.Path(__file__).resolve().parents[1]/'assistance/family_identity.py').read_bytes())
    script=base/'child';script.write_text((pathlib.Path(__file__).resolve().parents[1]/'assistance/family-help-child').read_text().replace('/etc/family-help/child.json',str(conf)))
    (base/'family_help_image.py').write_text((pathlib.Path(__file__).resolve().parents[1]/'assistance/family_help_image.py').read_text())
    draft='b'*32;(drafts/(draft+'.png')).write_bytes(original)
    def call(mode,payload=None,command=''):
        return subprocess.run(['/usr/bin/python3',str(script),mode],input=payload,capture_output=True,env=dict(os.environ,SSH_ORIGINAL_COMMAND=command),timeout=12)
    result=call('send-widget',json.dumps({'message':'Could you help? $(touch NEVER)','topic':'admin','draft':draft}).encode())
    assert result.returncode==0,result.stderr
    request=json.loads(call('poll').stdout);assert request['topic']=='admin'
    shot=call('poll',command='screenshot '+request['id']);assert shot.returncode==0,shot.stderr
    assert hashlib.sha256(shot.stdout).hexdigest()==request['screenshot']['sha256']
    assert b'private-test-metadata' not in shot.stdout
    assert call('poll',command='screenshot ../../etc/passwd').stdout==call('poll').stdout
    for payload in [b'[]',b'x'*2049,json.dumps({'message':'hi','topic':'bad'}).encode(),json.dumps({'message':'hi','topic':'help','command':'sudo'}).encode()]:
        assert call('send-widget',payload).returncode!=0
    cache=base/'cache';cache.mkdir()
    for i in range(12):(cache/(f'{i:032x}.png')).write_bytes(clean)
    prune(cache);assert len(list(cache.glob('*.png')))==8
    print('PASS: typed request and screenshot transport; hash bound to metadata; arbitrary fetch paths rejected; bounded cache')
# Dad accepts both legacy and new requests, and rejects extra command fields.
tree=ast.parse((pathlib.Path(__file__).resolve().parents[1]/'assistance/family-help-dad').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate')
ns={'re':re,'time':time};exec(compile(ast.Module(body=[node],type_ignores=[]),'<validate>','exec'),ns)
legacy={'id':'a'*32,'time':time.time(),'message':'hi'};assert ns['validate'](legacy)
assert ns['validate'](dict(legacy,topic='help',screenshot=info))
for candidate in [dict(legacy,command='sudo'),dict(legacy,topic='other'),dict(legacy,screenshot=dict(info,bytes=MAX_IMAGE+1)),dict(legacy,screenshot=dict(info,sha256='../../file'))]:
    try:ns['validate'](candidate)
    except ValueError:pass
    else:raise AssertionError(candidate)
print('PASS: Dad validates legacy/new requests and screenshot metadata without accepting executable fields')
