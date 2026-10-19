"""Optional offscreen Dino break card; no lock requests or household connections."""
import os,pathlib,shutil,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
if not shutil.which('quickshell'):raise SystemExit('Quickshell is required for this optional render check')
with tempfile.TemporaryDirectory() as directory:
    temp=pathlib.Path(directory);(temp/'Dino').symlink_to(root/'guardian',target_is_directory=True);(temp/'home').mkdir();(temp/'runtime').mkdir(mode=0o700)
    (temp/'shell.qml').write_text('''import QtQuick
import Quickshell
import "Dino" as Dino
ShellRoot {
    property bool bedtime: false
    FloatingWindow {
        id: window
        visible: true; implicitWidth: 800; implicitHeight: 740; color: "#111c17"
        Dino.BreakCard { id: card; anchors.centerIn: parent; width: 700; state: ({phase:"break",remaining_seconds:900,helpers:["dad","mom"]}) }
    }
    Timer { interval: 800; running: true; repeat: true; onTriggered: {
        if (card.implicitHeight > window.height) { console.error("FAIL_BREAK_BOUNDS"); Qt.quit(); return }
        if (!bedtime) {
            bedtime = true
            card.state = {healthy:true,blocked:true,reason:"outside-hours",helpers:["dad","mom"],hibernate:{enabled:true,remaining_seconds:300,error:""}}
            return
        }
        card.grabToImage(function(image) { image.saveToFile(Quickshell.env("FAMILY_BREAK_PREVIEW")); console.log("PASS_BREAK_CARD"); Qt.quit() })
    } }
}''')
    preview=os.environ.get('FAMILY_BREAK_PREVIEW',str(temp/'break.png'))
    env=dict(os.environ,HOME=str(temp/'home'),XDG_RUNTIME_DIR=str(temp/'runtime'),QT_QPA_PLATFORM='offscreen',QT_QPA_PLATFORMTHEME='basic',QT_QUICK_BACKEND='software',QT_QUICK_CONTROLS_STYLE='Basic',FAMILY_BREAK_PREVIEW=preview)
    env.pop('DISPLAY',None);env.pop('WAYLAND_DISPLAY',None);env.pop('WAYLAND_SOCKET',None)
    result=subprocess.run(['quickshell','--no-color','-p',str(temp)],env=env,capture_output=True,text=True,timeout=20)
    output=result.stdout+result.stderr
    assert result.returncode==0 and 'PASS_BREAK_CARD' in output and not any(word in output for word in ('ReferenceError','TypeError','Cannot assign','Unable to assign')),output
    assert pathlib.Path(preview).exists();print('PASS: baby Dino break card rendered within bounds with parent request controls')
