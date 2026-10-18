"""Optional installed-Omarchy headless bar rendering; never launches ask-dad."""
import os,pathlib,shutil,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1];omarchy=pathlib.Path('/usr/share/omarchy/shell')
if not shutil.which('quickshell') or not (omarchy/'Ui/qmldir').exists():raise SystemExit('Requires installed Omarchy and Quickshell; not tested')
with tempfile.TemporaryDirectory() as directory:
 tmp=pathlib.Path(directory)
 for name in ('Commons','Ui'):(tmp/name).symlink_to(omarchy/name,target_is_directory=True)
 (tmp/'Family').symlink_to(root/'desktop/ask-dad',target_is_directory=True)
 (tmp/'runtime').mkdir(mode=0o700);(tmp/'home').mkdir()
 (tmp/'shell.qml').write_text('''import QtQuick
import Quickshell
import "Family"
ShellRoot {
 Item {
  AskDad { id: widget }
  Timer { interval: 400; running: true; onTriggered: {
   if (widget.moduleName !== "community.family-lab.ask-dad" || widget.implicitWidth <= 0) throw new Error("Bad bar widget");
   console.log("PASS_ASK_DAD_BAR_QML"); Qt.quit();
  }}
 }
}
''')
 env=dict(os.environ,HOME=str(tmp/'home'),XDG_RUNTIME_DIR=str(tmp/'runtime'),QT_QPA_PLATFORM='offscreen',QT_QPA_PLATFORMTHEME='basic',QT_QUICK_CONTROLS_STYLE='Basic',QT_QUICK_BACKEND='software',OMARCHY_PATH='/usr/share/omarchy')
 env.pop('WAYLAND_DISPLAY',None);env.pop('DISPLAY',None)
 result=subprocess.run(['quickshell','--no-color','-p',str(tmp)],env=env,capture_output=True,text=True,timeout=20)
 output=result.stdout+result.stderr;print(output)
 assert result.returncode==0 and 'PASS_ASK_DAD_BAR_QML' in output and 'TypeError' not in output and 'ReferenceError' not in output
