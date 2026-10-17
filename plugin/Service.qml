import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import "UiModel.js" as Model

Item {
    id: service
    // Omarchy host injection: only the normal third-party scalar bar facade is read.
    property var shell: null
    property var manifest: null
    property string omarchyPath: ""
    readonly property string familyCommand: Quickshell.env("HOME") + "/.local/bin/family-lab"
    property var requests: []
    property double nowSeconds: Date.now() / 1000
    property string actionError: ""
    property string lastPayload: ""
    property string actionRequestId: ""
    property bool stateValid: false
    property bool inlineEnabled: false
    readonly property bool busy: actionProcess.running
    readonly property string barPosition: shell && shell.bar ? String(shell.bar.position) : "top"
    readonly property int barSize: shell && shell.bar && !shell.bar.barHidden ? shell.bar.barSize : 0

    function refresh() {
        if (!pollProcess.running) {
            pollProcess.running = true;
            pollTimeout.restart();
        }
    }
    function perform(id, kind, target) {
        if (busy)
            return;
        var command = Model.commandFor(familyCommand, id, kind, target);
        if (!command)
            return;
        actionError = "";
        actionRequestId = id;
        actionProcess.command = command;
        actionProcess.running = true;
    }
    function renewIfReady() {
        if (stateValid && inlineEnabled && (!requests.length || popupLoader.status === Loader.Ready) && !healthProcess.running)
            healthProcess.running = true;
    }
    Component.onCompleted: refresh()
    Timer {
        interval: 2000
        repeat: true
        running: true
        onTriggered: service.refresh()
    }
    Timer {
        interval: 1000
        repeat: true
        running: true
        onTriggered: service.nowSeconds = Date.now() / 1000
    }
    Timer {
        id: pollTimeout
        interval: 5000
        onTriggered: if (pollProcess.running)
            pollProcess.signal(9)
    }
    Process {
        id: pollProcess
        command: [service.familyCommand, "ui-state"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    if (text !== service.lastPayload) {
                        var parsed = Model.parse(text);
                        var next = parsed.requests;
                        service.stateValid = true;
                        service.inlineEnabled = parsed.enabled;
                        if (!next.length || !service.requests.length || next[0].id !== service.requests[0].id)
                            service.actionError = "";
                        service.requests = next;
                        service.lastPayload = text;
                    }
                } catch (e) {
                    service.requests = [];
                    service.lastPayload = "";
                    service.stateValid = false;
                }
            }
        }
        stderr: StdioCollector {} // Never log request data or private diagnostic paths.
        onExited: function (code) {
            pollTimeout.stop();
            if (code !== 0) {
                service.requests = [];
                service.lastPayload = "";
                service.stateValid = false;
            } else
                service.renewIfReady();
        }
    }
    Process {
        id: healthProcess
        command: [service.familyCommand, "ui-heartbeat"]
        stdout: StdioCollector {}
        stderr: StdioCollector {}
    }
    Process {
        id: actionProcess
        stdout: StdioCollector {}
        stderr: StdioCollector {}
        onExited: function (code) {
            service.actionError = code !== 0 && service.requests.length && service.requests[0].id === service.actionRequestId ? "could not complete action · request kept · try again" : "";
            service.refresh();
        }
    }
    Loader {
        id: popupLoader
        objectName: "familyPopupLoader"
        source: service.requests.length > 0 ? Qt.resolvedUrl("RequestPopup.qml") : ""
        onLoaded: {
            item.request = Qt.binding(function () {
                return service.requests.length ? service.requests[0] : ({
                        actions: []
                    });
            });
            item.waitingCount = Qt.binding(function () {
                return service.requests.length;
            });
            item.nowSeconds = Qt.binding(function () {
                return service.nowSeconds;
            });
            item.busy = Qt.binding(function () {
                return service.busy;
            });
            item.errorText = Qt.binding(function () {
                return service.actionError;
            });
            item.barPosition = Qt.binding(function () {
                return service.barPosition;
            });
            item.barSize = Qt.binding(function () {
                return service.barSize;
            });
            item.fontFamily = Qt.binding(function () {
                return service.shell && service.shell.bar && service.shell.bar.fontFamily ? service.shell.bar.fontFamily : Style.font.family;
            });
            item.actionRequested.connect(service.perform);
            service.renewIfReady();
        }
    }
}
