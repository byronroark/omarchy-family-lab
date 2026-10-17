"""Optional headless rendering test against an installed Omarchy/Quickshell runtime."""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

project = pathlib.Path(__file__).resolve().parents[1]
omarchy = pathlib.Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy'))
if not shutil.which('quickshell') or not (omarchy / 'shell/Commons/qmldir').exists():
    raise SystemExit('Requires the actual installed Omarchy shell and Quickshell; no runtime was tested.')
with tempfile.TemporaryDirectory() as directory:
    temp = pathlib.Path(directory)
    for name in ('Commons', 'Ui'):
        (temp / name).symlink_to(omarchy / 'shell' / name, target_is_directory=True)
    (temp / 'Family').symlink_to(project / 'plugin', target_is_directory=True)
    (temp / 'shell.qml').write_text((project / 'tests/qml/inline.qml').read_text())
    (temp / 'runtime').mkdir(mode=0o700)
    (temp / 'home').mkdir()
    (temp / 'home/.local/bin').mkdir(parents=True)
    stub = temp / 'home/.local/bin/family-lab'
    stub.write_text('#!/usr/bin/env python3\nprint(\'{"version":1,"enabled":false,"paused":false,"requests":[]}\')\n')
    stub.chmod(0o700)
    env = dict(os.environ, HOME=str(temp/'home'), XDG_RUNTIME_DIR=str(temp/'runtime'),
               XDG_CONFIG_HOME=str(temp/'home/.config'), XDG_CACHE_HOME=str(temp/'home/.cache'),
               QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='basic',
               QT_QUICK_CONTROLS_STYLE='Basic', QT_QUICK_BACKEND='software',
               OMARCHY_PATH=str(omarchy), FAMILY_LAB_PREVIEW_DIR=str(temp))
    env.pop('WAYLAND_DISPLAY', None)
    env.pop('DISPLAY', None)
    result = subprocess.run(['quickshell', '--no-color', '-p', str(temp)], env=env,
                            capture_output=True, text=True, timeout=20)
    output = result.stdout + result.stderr
    print(output)
    assert result.returncode == 0 and 'PASS_INLINE_QML' in output, 'Headless QML check failed'
    assert 'TypeError' not in output and 'ReferenceError' not in output
    destination = os.environ.get('FAMILY_LAB_PREVIEW_DIR')
    if destination:
        dest = pathlib.Path(destination)
        dest.mkdir(parents=True, exist_ok=True)
        for name in ('inline-dark.png', 'inline-light.png'):
            shutil.copyfile(temp / name, dest / name)
