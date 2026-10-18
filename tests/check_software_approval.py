import hashlib,importlib.machinery,json,os,pathlib,subprocess,sys,tempfile,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'assistance'))
from family_software import validate_software,validate_request,read_private
request={'id':'a'*32,'time':time.time(),'message':'Please approve','topic':'admin','software':{'action':'install','packages':['extra/jq']}}
assert validate_request(request)==request
for software in [ {'action':'install','packages':['--config=/tmp/evil']},{'action':'install','packages':['/tmp/a.pkg.tar.zst']},{'action':'install','packages':['extra/jq;id']},{'action':'install','packages':['extra/$(id)']},{'action':'install','packages':['extra/jq','extra/jq']},{'action':'update','packages':['extra/jq']},{'action':'shell','packages':[]},{'action':'install','packages':['extra/jq'],'command':'id'}]:
 try:validate_software(software)
 except ValueError:pass
 else:raise AssertionError(software)
for bad in [dict(request,time=time.time()-901),dict(request,time=float('nan')),dict(request,command='id'),dict(request,id='../../file')]:
 try:validate_request(bad)
 except ValueError:pass
 else:raise AssertionError(bad)
print('PASS: only typed install/update requests; flags, files, command injection, duplicate packages, extra fields, expiry and non-finite times rejected')
with tempfile.TemporaryDirectory() as folder:
 path=pathlib.Path(folder)/'approval.json';path.write_text(json.dumps(request));path.chmod(0o600)
 assert read_private(path,os.getuid())==request
 link=pathlib.Path(folder)/'link';link.symlink_to(path)
 for target,owner in [(link,os.getuid()),(path,os.getuid()+1)]:
  try:read_private(target,owner)
  except (OSError,ValueError):pass
  else:raise AssertionError('Unsafe approval accepted')
 path.chmod(0o666)
 try:read_private(path,os.getuid())
 except ValueError:pass
 else:raise AssertionError('Writable approval accepted')
print('PASS: symlink, wrong-owner and writable approval snapshots rejected')
for filename in ['family-software-execute','family-software-admin','family-software-request','family-help-dad','family-help-widget','family_software.py']:
 source=pathlib.Path(__file__).resolve().parents[1]/'assistance'/filename
 compile(source.read_text(),str(source),'exec')
print('PASS: all software and existing help components compile')
result=subprocess.run(['/usr/bin/python3',str(pathlib.Path(__file__).resolve().parents[1]/'assistance/family-software-execute'),'approve','a'*32],capture_output=True,text=True)
assert result.returncode!=0 and 'authentication required' in result.stderr
print('PASS: executor refuses an unauthenticated normal account')
