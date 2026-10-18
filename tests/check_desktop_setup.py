"""All desktop writes are isolated; no compositor or shell command executes."""
import importlib.machinery,importlib.util,os,pathlib,subprocess,tempfile,types
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
loader=importlib.machinery.SourceFileLoader('desktop_setup',str(ROOT/'assistance/family-help-desktop-setup'));spec=importlib.util.spec_from_loader(loader.name,loader);module=importlib.util.module_from_spec(spec);loader.exec_module(module)
with tempfile.TemporaryDirectory() as temp:
 home=pathlib.Path(temp);main=home/'.config/hypr/hyprland.lua';main.parent.mkdir(parents=True);original='-- Personal overrides\nrequire("hypr.monitors")\n';main.write_text(original)
 calls=[]
 def fake(command):calls.append(command);return types.SimpleNamespace(stdout='')
 with patch.object(module,'run',side_effect=fake):module.install(home,ROOT/'desktop/ask-dad')
 assert main.read_text().count(module.START)==1 and original.strip() in main.read_text()
 assert ['/usr/bin/hyprctl','reload'] in calls and ['/usr/bin/hyprctl','configerrors'] in calls
 assert any(x[-4:]==['--section','right','--index','0'] for x in calls)
 files={x:x.read_bytes() for x in home.rglob('*') if x.is_file()}
 with patch.object(module,'run',side_effect=fake):module.install(home,ROOT/'desktop/ask-dad')
 assert all(p.read_bytes()==data for p,data in files.items())
 # Inject a compositor failure after writes, while mocking even rollback's reload.
 main.write_text(original);rule=main.with_name('family-help.lua');rule.unlink()
 def fail(command):
  if command[-1]=='reload':raise subprocess.CalledProcessError(1,command)
  return types.SimpleNamespace(stdout='')
 with patch.object(module,'run',side_effect=fail),patch.object(module.subprocess,'run'):
  try:module.install(home,ROOT/'desktop/ask-dad')
  except subprocess.CalledProcessError:pass
  else:raise AssertionError('Failure was not propagated')
 assert main.read_text()==original and not rule.exists()
print('PASS: user-only icon/rule installation, preserved configuration, idempotence, compositor validation and rollback; no live desktop changes')
