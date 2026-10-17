pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui as Ui
import "Flow.js" as DinoFlow

Rectangle {
    id: card
    required property var state
    signal actionRequested(string action)
    color: Color.notifications.background
    implicitWidth: Style.space(700)
    implicitHeight: content.implicitHeight + Style.space(48)
    Accessible.name: title.text
    ColumnLayout {
        id: content
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: Style.space(24) }
        spacing: Style.space(16)
        PixelDino {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: Style.space(192)
            Layout.preferredHeight: Style.space(192)
            sleepy: card.state.phase === "blocked" || card.state.phase === "hibernate-error"
        }
        Text {
            id: title
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
            color: Color.notifications.text
            font { family: Style.font.family; pixelSize: Style.font.subtitle; bold: true }
            text: card.state.phase === "warning" ? "Dino bedtime is coming" :
                  card.state.phase === "saving" ? "Save your adventure!" :
                  card.state.phase === "hibernate-error" ? "Dino needs a parent's help" : "Time for a little rest"
        }
        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
            color: Color.notifications.text
            font { family: Style.font.family; pixelSize: Style.font.body }
            text: card.state.phase === "saving" ? "Save your files and finish up before your PC rests." :
                  card.state.phase === "time-up" ? "Great exploring today! You have a little time to save your work." :
                  card.state.phase === "warning" ? "You have a few minutes left. Start saving your work." :
                  card.state.phase === "hibernate-error" ? "Your PC could not hibernate. Please ask a parent for help." :
                  "Today's exploring is finished. Your saved files are still on this PC."
        }
        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            textFormat: Text.PlainText
            visible: card.state.phase === "time-up" || card.state.phase === "saving"
            text: DinoFlow.countdown(card.state.remaining)
            color: Color.accent
            font { family: Style.font.family; pixelSize: Style.font.subtitle * 2; bold: true }
        }
        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            textFormat: Text.PlainText
            wrapMode: Text.WrapAnywhere
            color: Color.muted
            font { family: Style.font.family; pixelSize: Style.font.bodySmall }
            text: card.state.nextLabel ? "Next adventure: " + card.state.nextLabel : "Ask a parent to check your next adventure time."
        }
        Flow {
            Layout.fillWidth: true
            spacing: Style.space(10)
            Repeater {
                model: ["sleep", "save", "ask-mom", "ask-dad"]
                delegate: Ui.Button {
                    required property string modelData
                    visible: DinoFlow.permitted(card.state, modelData)
                    text: modelData === "sleep" ? "Hibernate now" : modelData === "save" ? "Use save time" : modelData === "ask-mom" ? "Ask Mom" : "Ask Dad"
                    onClicked: card.actionRequested(modelData)
                }
            }
        }
    }
}
