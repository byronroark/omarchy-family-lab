pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui as Ui

Ui.BorderSurface {
    id: card
    required property var request
    property int waitingCount: 1
    property double nowSeconds: Date.now() / 1000
    property bool busy: false
    property string errorText: ""
    property string fontFamily: Style.font.family
    signal actionRequested(string requestId, string kind, string target)

    objectName: "familyRequestCard"
    implicitWidth: Style.space(440)
    implicitHeight: content.implicitHeight + inset * 2
    readonly property real inset: Style.space(16) + borderTop
    color: Color.notifications.background
    radius: Style.cornerRadius
    borderSpec: Border.surfaceSpec("notifications", "border", Color.notifications.border, Style.normalBorderWidth)
    Accessible.name: "Family Lab help request from " + String(request.peer || "")
    FontMetrics {
        id: buttonMetrics
        font.family: card.fontFamily
        font.pixelSize: Style.font.bodySmall
    }

    ColumnLayout {
        id: content
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            margins: card.inset
        }
        spacing: Style.space(12)

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "[ family lab ]"
                textFormat: Text.PlainText
                color: Color.accent
                font {
                    family: card.fontFamily
                    pixelSize: Style.font.body
                    bold: true
                }
            }
            Item {
                Layout.fillWidth: true
            }
            Text {
                text: card.waitingCount > 1 ? String(card.waitingCount) + " waiting" : "help requested"
                textFormat: Text.PlainText
                color: Color.muted
                font {
                    family: card.fontFamily
                    pixelSize: Style.font.bodySmall
                }
            }
        }
        Text {
            Layout.fillWidth: true
            text: "> " + String(card.request.peer || "learner")
            textFormat: Text.PlainText
            wrapMode: Text.WrapAnywhere
            color: Color.notifications.text
            font {
                family: card.fontFamily
                pixelSize: Style.font.subtitle
                bold: true
            }
        }
        Text {
            Layout.fillWidth: true
            visible: String(card.request.via || "").length > 0
            text: "forwarded via " + String(card.request.via || "")
            textFormat: Text.PlainText
            color: Color.muted
            font {
                family: card.fontFamily
                pixelSize: Style.font.bodySmall
            }
        }
        Flickable {
            id: messageScroll
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(message.implicitHeight, Style.space(180))
            contentHeight: message.implicitHeight
            contentWidth: width
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            interactive: contentHeight > height
            Text {
                id: message
                objectName: "requestMessage"
                width: messageScroll.width
                text: String(card.request.message || "")
                textFormat: Text.PlainText
                wrapMode: Text.WrapAnywhere
                color: Color.notifications.text
                font {
                    family: card.fontFamily
                    pixelSize: Style.font.body
                }
            }
        }
        Text {
            visible: messageScroll.interactive
            text: "scroll to read full message"
            textFormat: Text.PlainText
            color: Color.muted
            font {
                family: card.fontFamily
                pixelSize: Style.font.bodySmall
            }
        }
        Flow {
            Layout.fillWidth: true
            Layout.preferredHeight: implicitHeight
            spacing: Style.space(6)
            Repeater {
                model: card.request.actions || []
                delegate: Ui.Button {
                    required property var modelData
                    objectName: "action-" + modelData.kind + "-" + String(modelData.target || "")
                    text: buttonMetrics.elidedText("[ " + String(modelData.label) + " ]", Qt.ElideRight, Math.max(40, card.width - card.inset * 2 - Style.space(24)))
                    tooltipText: String(modelData.label)
                    fontFamily: card.fontFamily
                    fontSize: Style.font.bodySmall
                    horizontalPadding: Style.space(8)
                    verticalPadding: Style.space(7)
                    focusable: true
                    bordered: true
                    enabled: !card.busy && card.nowSeconds < Number(card.request.expires)
                    opacity: enabled ? 1 : 0.5
                    // Bound labels come only from the local CLI's validated action set.
                    onClicked: if (enabled)
                        card.actionRequested(String(card.request.id), String(modelData.kind), String(modelData.target || ""))
                }
            }
        }
        Text {
            Layout.fillWidth: true
            text: card.errorText.length > 0 ? card.errorText : card.busy ? "working…" : "view only · control needs local approval"
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
            color: card.errorText.length > 0 ? Color.urgent : Color.muted
            font {
                family: card.fontFamily
                pixelSize: Style.font.bodySmall
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(1, Style.normalBorderWidth)
            color: Color.notifications.border
            Rectangle {
                width: parent.width * Math.max(0, Math.min(1, (Number(card.request.expires) - card.nowSeconds) / 600))
                height: parent.height
                color: Color.notifications.countdown
            }
        }
    }
}
