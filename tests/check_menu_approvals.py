import json,pathlib,sys,types
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'assistance'))
import family_menu as menu
from family_software import validate_software
catalog=menu.catalog();items={k:v for k,v in catalog.items() if not k.startswith('_')}
for key,item in items.items():
 assert validate_software({'action':'menu','packages':[],'menu':key})['menu']==key
 if item.get('packages'):assert menu.package_command(item['packages'])[:4]==['/usr/bin/pacman','-S','--needed','--']
 assert item['mode'] in ('manual','package','script','agent','controllers')
for value in [ {'action':'menu','packages':['extra/jq'],'menu':'install.gaming.retroarch'}, {'action':'menu','packages':[],'menu':'install.gaming.retroarch;id'}, {'action':'menu','packages':[],'menu':'../../file'}, {'action':'menu','packages':[],'menu':'install.unknown'}, {'action':'menu','packages':[],'menu':'install.gaming.retroarch','command':'sudo sh'} ]:
 try:validate_software(value)
 except ValueError:pass
 else:raise AssertionError(value)
print('PASS: all registered menu IDs validate; unknown IDs, extra arguments, commands and traversal rejected')
for package in ['--config=/tmp/evil','/tmp/local.pkg.tar.zst','jq;id','$(id)']:
 try:menu.package_command([package])
 except ValueError:pass
 else:raise AssertionError(package)
print('PASS: catalog package commands cannot accept options, paths or shell fragments')
command=menu.child_command(types.SimpleNamespace(pw_uid=12345,pw_gid=12346,pw_name='learner',pw_dir='/tmp/learner'),'setup.default.agent.codex')
assert '--no-new-privs' in command and '--init-groups' in command and '--reuid=12345' in command and '--regid=12346' in command
assert command[-3:]==['/usr/local/libexec/family-menu-action','--user','setup.default.agent.codex']
assert not any('SSH_AUTH_SOCK=' in x or 'SUDO_' in x for x in command)
assert command[command.index('/usr/bin/env')+1]=='-i'
print('PASS: personal actions drop to the child identity with no new privileges or parent environment')
# Manual requests must execute absolutely no installer, even after approval.
old_plan=menu.plan;old_subprocess=menu.subprocess
menu.plan=lambda _:({'mode':'manual','original':'DO NOT EXECUTE'},[])
menu.subprocess=types.SimpleNamespace(run=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Manual command was executed')))
assert menu.run('manual.test',{}, {})==('manual-review',0)
menu.plan=old_plan;menu.subprocess=old_subprocess
print('PASS: manual-review approval does not execute the original menu action')
retro=items['install.gaming.retroarch'];assert len(retro['packages'])>30 and retro['mode']=='script'
assert 'install.gaming.retro-launcher' not in items
assert items['install.gaming.xbox-controllers']['mode']=='controllers'
assert 'input' in items['install.gaming.xbox-controllers']['notice']
for name in ['family_menu.py','family_software.py','family-menu-action','family-software-request','family-software-admin','family-software-execute','family-help-widget']:
 p=pathlib.Path(__file__).resolve().parents[1]/'assistance'/name;compile(p.read_text(),str(p),'exec')
print('PASS: correct RetroArch entry, controller permission notice and syntax checks')
