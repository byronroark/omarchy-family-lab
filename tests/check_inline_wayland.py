"""Optional real Wayland smoke test: briefly shows ONE synthetic card, no network/actions."""
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import time

if not os.environ.get('WAYLAND_DISPLAY'):
    raise SystemExit('Requires a real Wayland desktop. This check briefly displays a synthetic request card.')
project = pathlib.Path(__file__).resolve().parents[1]
omarchy = pathlib.Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy'))
with tempfile.TemporaryDirectory() as directory:
    temp = pathlib.Path(directory)
    for name in ('Commons', 'Ui'):
        (temp / name).symlink_to(omarchy/'shell'/name, target_is_directory=True)
    (temp / 'Family').symlink_to(project/'plugin', target_is_directory=True)
    home = temp/'home'
    (home/'.local/bin').mkdir(parents=True)
    request = {'id': 'a'*32, 'peer': 'learner-a', 'via': '',
               'message': 'Synthetic interface test. No remote computer is connected.',
               'expires': time.time()+60, 'actions': [{'kind': 'open', 'label': 'Open terminal'},
                     {'kind': 'forward', 'target': 'mom', 'label': 'Ask Mom'}, {'kind': 'dismiss', 'label': 'Dismiss'}]}
    fixture = json.dumps({'version': 1, 'enabled': True, 'paused': False, 'requests': [request]})
    stub = home/'.local/bin/family-lab'
    stub.write_text('#!/usr/bin/env python3\nimport sys\nif sys.argv[1:] == ["ui-state"]:\n    print(' + repr(fixture) + ')\nelse:\n    sys.exit(1)\n')
    stub.chmod(0o700)
    (temp/'shell.qml').write_text('''import QtQuick
import Quickshell
import "Family" as Family
ShellRoot {
    Family.Service { id: service }
    Timer {
        interval: 2000; running: true
        onTriggered: {
            var found = null
            for (var i = 0; i < service.children.length; i++)
                if (service.children[i].objectName === "familyPopupLoader") found = service.children[i]
            if (found && found.status === Loader.Ready && found.item && found.item.visible)
                console.log("PASS_WAYLAND_POPUP")
            else console.error("FAIL_WAYLAND_POPUP")
            Qt.quit()
        }
    }
}
''')
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home/'.config'),
               XDG_CACHE_HOME=str(home/'.cache'), QT_QPA_PLATFORM='wayland',
               QT_QPA_PLATFORMTHEME='basic', QT_QUICK_CONTROLS_STYLE='Basic')
    result = subprocess.run(['quickshell', '--no-color', '-p', str(temp)], env=env,
                            capture_output=True, text=True, timeout=15)
    output = result.stdout + result.stderr
    print(output)
    assert result.returncode == 0 and 'PASS_WAYLAND_POPUP' in output
    assert not any(marker in output for marker in ('TypeError', 'ReferenceError', 'Unable to assign', 'Cannot assign'))
