import QtQuick
import Quickshell
import qs.Commons
import "Family" as Family

ShellRoot {
    id: harness
    property string failure: ""
    property string phase: "dark"
    property var received: []
    Loader {
        id: serviceSmoke
        source: "Family/Service.qml"
        onStatusChanged: if (status === Loader.Error)
            harness.check(false, "Plugin service failed to load")
    }
    function check(value, description) {
        if (!value) {
            failure = description;
            console.error("FAIL_INLINE_QML: " + description);
            Qt.quit();
        }
    }
    function find(item, name) {
        if (item.objectName === name)
            return item;
        var children = item.children || [];
        for (var i = 0; i < children.length; i++) {
            var found = find(children[i], name);
            if (found)
                return found;
        }
        return null;
    }
    FloatingWindow {
        id: window
        visible: true
        implicitWidth: 520
        implicitHeight: card.implicitHeight + 48
        color: Color.background
        Family.RequestCard {
            id: card
            x: 24
            y: 24
            width: 472
            waitingCount: 2
            nowSeconds: 1000
            request: ({
                    id: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    peer: "learner-a",
                    via: "",
                    message: "Could you help me understand this terminal error? I want to learn what the command does before trying again.",
                    expires: 1420,
                    actions: [
                        {
                            kind: "open",
                            label: "Open terminal"
                        },
                        {
                            kind: "forward",
                            label: "Ask Mom",
                            target: "mom"
                        },
                        {
                            kind: "dismiss",
                            label: "Dismiss"
                        }
                    ]
                })
            onActionRequested: function (id, kind, target) {
                harness.received.push([id, kind, target]);
            }
        }
    }
    Timer {
        interval: 500
        running: true
        repeat: true
        onTriggered: {
            var open = harness.find(card, "action-open-");
            var mom = harness.find(card, "action-forward-mom");
            var dismiss = harness.find(card, "action-dismiss-");
            harness.check(open && mom && dismiss, "Inline actions must exist");
            if (harness.failure)
                return;
            if (harness.phase === "dark") {
                harness.check(card.implicitHeight > 200 && card.implicitHeight < 650, "Card height fits content");
                harness.check(serviceSmoke.status === Loader.Ready, "Actual plugin entry point loaded");
                harness.check(harness.find(card, "requestMessage").textFormat === Text.PlainText, "Plain text message");
                mom.clicked();
                harness.check(harness.received.length === 1 && harness.received[0][1] === "forward" && harness.received[0][2] === "mom", "Ask Mom forwards the fixed target");
                card.busy = true;
                mom.clicked();
                harness.check(harness.received.length === 1, "Busy cards cannot dispatch again");
                card.busy = false;
                card.nowSeconds = 1500;
                open.clicked();
                harness.check(harness.received.length === 1, "Expired cards cannot dispatch");
                card.nowSeconds = 1000;
                card.grabToImage(function (result) {
                    harness.check(result.saveToFile(Quickshell.env("FAMILY_LAB_PREVIEW_DIR") + "/inline-dark.png"), "Dark image saved");
                    Color.background = "#f5f2ea";
                    Color.foreground = "#252a34";
                    Color.accent = "#245f91";
                    Color.muted = "#626b76";
                    Color.shellValues = ({});
                    harness.phase = "light";
                });
                harness.phase = "rendering";
            } else if (harness.phase === "light") {
                harness.check(card.color === Color.notifications.background, "Palette tracks theme");
                open.forceActiveFocus();
                harness.check(open.activeFocus, "Keyboard focus available");
                card.grabToImage(function (result) {
                    harness.check(result.saveToFile(Quickshell.env("FAMILY_LAB_PREVIEW_DIR") + "/inline-light.png"), "Light image saved");
                    Style.fontBaseSize = 20;
                    card.width = 320;
                    card.request = Object.assign({}, card.request, {
                        message: "long-message-".repeat(23),
                        actions: [
                            {
                                kind: "open",
                                label: "Open terminal"
                            },
                            {
                                kind: "forward",
                                target: "mom",
                                label: "Ask Mom"
                            },
                            {
                                kind: "dismiss",
                                label: "Dismiss"
                            }
                        ]
                    });
                    harness.phase = "large";
                });
                harness.phase = "rendering";
            } else if (harness.phase === "large") {
                harness.check(open.width <= card.width - card.inset * 2, "Buttons fit narrow card with larger text");
                harness.check(mom.width <= card.width - card.inset * 2, "Forward button fits larger text");
                harness.check(card.implicitHeight < 1000, "Long message is scrollable, not unbounded");
                if (!harness.failure)
                    console.log("PASS_INLINE_QML");
                Qt.quit();
            }
        }
    }
    Timer {
        interval: 12000
        running: true
        onTriggered: {
            console.error("FAIL_INLINE_QML: timeout");
            Qt.quit();
        }
    }
}
