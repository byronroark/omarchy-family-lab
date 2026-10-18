import QtQuick
import Quickshell
import qs.Commons
import "Guardian" as Guardian

ShellRoot {
    id: harness
    property bool failed: false
    Loader {
        source: "Guardian/preview.qml"
        onStatusChanged: if (status === Loader.Error) {
            console.error("FAIL_DINO_QML: preview failed to load"); Qt.quit()
        }
    }
    FloatingWindow {
        id: window
        visible: true
        implicitWidth: 820
        implicitHeight: 720
        color: Color.notifications.background
        Guardian.DinoCard {
            id: card
            anchors.centerIn: parent
            width: 720
            state: ({version: 1, phase: "time-up", remaining: 300, nextLabel: "Example Sunday 09:00 UTC", helpers: ["mom", "dad"]})
        }
    }
    Timer {
        interval: 900
        running: true
        onTriggered: {
            if (card.implicitHeight > window.height || card.width > window.width) {
                console.error("FAIL_DINO_QML: card bounds"); harness.failed = true; Qt.quit(); return
            }
            card.grabToImage(function(result) {
                result.saveToFile(Quickshell.env("FAMILY_LAB_PREVIEW_DIR") + "/dino-time-up.png")
                card.state = {version: 1, phase: "blocked", remaining: 300, nextLabel: "Example Sunday 09:00 UTC", helpers: ["dad"]}
                finish.start()
            })
        }
    }
    Timer {
        id: finish
        interval: 400
        onTriggered: card.grabToImage(function(result) {
            result.saveToFile(Quickshell.env("FAMILY_LAB_PREVIEW_DIR") + "/dino-blocked.png")
            console.log("PASS_DINO_QML")
            Qt.quit()
        })
    }
}
