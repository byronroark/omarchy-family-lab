pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
Rectangle {
    id: card
    required property var state
    signal requestChange(string helper, string change, int minutes)
    color: "#18231f"
    implicitWidth: 700
    implicitHeight: content.implicitHeight + 48
    ColumnLayout {
        id: content
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 24 }
        spacing: 16
        PixelDino { Layout.alignment: Qt.AlignHCenter; Layout.preferredWidth: 180; Layout.preferredHeight: 180; sleepy: true }
        Label { text: card.state.reason === "outside-hours" ? "Dino bedtime" : "Dino is taking a little break"; color: "#e4f2e9"; font.pixelSize: 28; font.bold: true; Layout.alignment: Qt.AlignHCenter }
        Label { text: "Stretch, get a drink, or find an adventure away from the screen."; color: "#e4f2e9"; wrapMode: Text.WordWrap; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
        Label {
            text: card.state.reason === "outside-hours" ? (card.state.next_allowed ? "Next adventure: " + card.state.next_allowed.label : "Ask a parent about your next adventure.") : card.state.phase === "due" ? "Preparing your protected break…" : Math.floor(card.state.remaining_seconds / 60) + ":" + (card.state.remaining_seconds % 60 < 10 ? "0" : "") + card.state.remaining_seconds % 60
            color: "#80c7a3"; font.pixelSize: 38; Layout.alignment: Qt.AlignHCenter
        }
        Label { text: "Your work stays open. Asking a parent does not pause the break."; color: "#b0c4b8"; wrapMode: Text.WordWrap; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
        ComboBox { id: change; visible: card.state.reason !== "outside-hours"; model: ["Skip this break", "Shorten by 5 minutes", "Extend by 5 minutes"]; Layout.alignment: Qt.AlignHCenter }
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Repeater {
                model: card.state.helpers || []
                delegate: Button {
                    required property string modelData
                    text: modelData === "mom" ? "Ask Mom" : modelData === "dad" ? "Ask Dad" : "Ask parent"
                    onClicked: card.requestChange(modelData, change.currentIndex === 0 ? "skip" : change.currentIndex === 1 ? "shorten" : "extend", change.currentIndex === 0 ? 0 : 5)
                }
            }
        }
        Label { text: card.state.requestStatus || "Only an enrolled parent can approve a change to this break."; color: "#b0c4b8"; wrapMode: Text.WordWrap; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
    }
}
