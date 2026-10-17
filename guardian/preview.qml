import QtQuick
import QtQuick.Window
import qs.Commons
import "Flow.js" as DinoFlow

Window {
    id: preview
    width: 820
    height: 760
    visible: true
    title: "Family Lab Dino - design preview only"
    color: Color.notifications.background
    property var previewState: ({version: 1, phase: "time-up", remaining: 180,
                                nextLabel: "Example schedule - Sunday 09:00 local time", helpers: ["mom", "dad"]})
    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: preview.previewState = DinoFlow.tick(preview.previewState, 1)
    }
    Column {
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 700)
        spacing: 12
        Text {
            width: parent.width
            text: "DESIGN PREVIEW - does not lock, contact anyone, or hibernate"
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
            color: Color.urgent
            font.family: Style.font.family
        }
        DinoCard {
            width: parent.width
            state: previewState
            onActionRequested: function(action) {
                if (action === "save") previewState = Object.assign({}, previewState, {phase: "saving"})
                if (action === "sleep") previewState = Object.assign({}, previewState, {phase: "blocked", remaining: 0})
            }
        }
    }
}
