import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import "Dino" as Dino
ShellRoot {
    id: root
    property var state: ({healthy:false,blocked:true,phase:"due",remaining_seconds:0,helpers:[],requestStatus:"Connecting to your protected break…"})
    property string error: ""
    property bool sending: false
    function refresh() { if (!poll.running) poll.running = true }
    function protect() {
        if (session.secure && root.state.healthy && root.state.episode && root.state.phase === "due" && !ack.running) {
            ack.command = ["/usr/local/libexec/family-lab-policy", "guard", "protected", root.state.episode]
            ack.running = true
        }
    }
    function ask(helper, change, minutes) {
        if (!root.state.healthy || send.running) return
        if (root.state.reason === "outside-hours") {
            send.command = ["/usr/local/libexec/family-lab-policy","guard","help",helper]; send.running = true; return
        }
        if (!root.state.episode) return
        send.command = ["/usr/local/libexec/family-lab-policy", "guard", "ask", helper, change, String(minutes), root.state.episode, String(root.state.revision)]
        send.running = true
    }
    WlSessionLock {
        id: session
        locked: true
        onSecureChanged: root.protect()
        WlSessionLockSurface {
            Rectangle {
                anchors.fill: parent
                color: "#111c17"
                Dino.BreakCard {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 40,700)
                    state: Object.assign({},root.state,{requestStatus:root.error || root.state.requestStatus || "Only a parent can approve a break change."})
                    onRequestChange: function(helper,change,minutes) { root.ask(helper,change,minutes) }
                    onHibernateNow: {
                        if (session.secure && root.state.hibernate && root.state.hibernate.enabled && !send.running) {
                            send.command = ["/usr/local/libexec/family-lab-policy","guard","hibernate",root.state.hibernate.episode]
                            send.running = true
                        }
                    }
                }
                // This is a break guard, not an account-password replacement.
                // Existing normal account locks keep their own authentication.
                Rectangle {
                    anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; bottomMargin: 20 }
                    width: 250; height: 48; radius: 8; color: "#80c7a3"
                    visible: root.state.healthy && !root.state.blocked
                    Text { anchors.centerIn: parent; text: "Return to my work"; color: "#111c17"; font.pixelSize: 18 }
                    MouseArea { anchors.fill: parent; onClicked: { if (root.state.healthy && !root.state.blocked && !release.running) release.running = true } }
                }
            }
        }
    }
    Process {
        id: poll
        command: ["/usr/local/libexec/family-lab-policy","guard", session.secure ? "get-secure" : "get"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var value = JSON.parse(text)
                    if (typeof value.healthy !== "boolean" || typeof value.blocked !== "boolean") throw Error("Invalid policy status")
                    root.state = value; root.error = ""; root.protect()
                } catch (e) { root.state = Object.assign({},root.state,{healthy:false,blocked:true}); root.error = "Waiting for the policy service. Your break screen stays protected." }
            }
        }
        onExited: function(code,status) { if (code !== 0) { root.state = Object.assign({},root.state,{healthy:false,blocked:true}); root.error = "Policy service unavailable. Ask a parent to check it." } }
    }
    Process {
        id: release
        command: ["/usr/local/libexec/family-lab-policy","guard","release"]
        stdout: StdioCollector { onStreamFinished: {
            try { if (JSON.parse(text).allowed === true) { session.locked = false; Qt.quit() } }
            catch (e) { root.error = "Permission changed. Your screen stays protected." }
        } }
    }
    Process { id: ack; onExited: root.refresh() }
    Process {
        id: send
        onExited: function(code,status) { root.error = code === 0 ? (send.command[2] === "hibernate" ? "Hibernation requested. Your work stays protected." : "Request sent. Your break keeps counting down.") : "Could not confirm delivery. Please wait before trying again."; root.refresh() }
    }
    Timer { interval: 1000; running: true; repeat: true; onTriggered: root.refresh() }
    Component.onCompleted: root.refresh()
}
