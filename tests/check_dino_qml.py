"""Optional real Omarchy offscreen rendering. No locking, power calls, network or enrollment."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]
omarchy=Path('/usr/share/omarchy')
if not shutil.which('quickshell') or not (omarchy/'shell/Commons/qmldir').exists():
    raise SystemExit('Requires installed Omarchy and Quickshell; no runtime was tested.')
with tempfile.TemporaryDirectory() as directory:
    temp=Path(directory)
    for name in ('Commons','Ui'):(temp/name).symlink_to(omarchy/'shell'/name,target_is_directory=True)
    (temp/'Guardian').symlink_to(root/'guardian',target_is_directory=True)
    (temp/'shell.qml').write_text((root/'tests/qml/dino.qml').read_text())
    (temp/'home').mkdir();(temp/'runtime').mkdir(mode=0o700)
    env=dict(os.environ,HOME=str(temp/'home'),XDG_RUNTIME_DIR=str(temp/'runtime'),
             XDG_CONFIG_HOME=str(temp/'home/.config'),XDG_CACHE_HOME=str(temp/'home/.cache'),
             QT_QPA_PLATFORM='offscreen',QT_QPA_PLATFORMTHEME='basic',QT_QUICK_CONTROLS_STYLE='Basic',
             QT_QUICK_BACKEND='software',OMARCHY_PATH=str(omarchy),FAMILY_LAB_PREVIEW_DIR=str(temp))
    env.pop('WAYLAND_DISPLAY',None);env.pop('DISPLAY',None)
    result=subprocess.run(['quickshell','--no-color','-p',str(temp)],env=env,capture_output=True,text=True,timeout=20)
    output=result.stdout+result.stderr
    print(output)
    assert result.returncode==0 and 'PASS_DINO_QML' in output
    assert 'ReferenceError' not in output and 'TypeError' not in output
    if os.environ.get('FAMILY_LAB_PREVIEW_DIR'):
        dest=Path(os.environ['FAMILY_LAB_PREVIEW_DIR']);dest.mkdir(parents=True,exist_ok=True)
        for name in ('dino-time-up.png','dino-blocked.png'):shutil.copyfile(temp/name,dest/name)
