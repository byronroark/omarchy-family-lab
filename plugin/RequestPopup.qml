import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Commons

PanelWindow {
    id: window
    property var request: ({
            actions: []
        })
    property int waitingCount: 0
    property double nowSeconds: Date.now() / 1000
    property bool busy: false
    property string errorText: ""
    property string barPosition: "top"
    property int barSize: 0
    property string fontFamily: Style.font.family
    signal actionRequested(string requestId, string kind, string target)
    visible: waitingCount > 0 && nowSeconds < Number(request.expires)
    screen: Quickshell.screens.length > 0 ? Quickshell.screens[0] : null
    anchors {
        bottom: true
        right: true
    }
    margins {
        bottom: Style.gapsOut + (barPosition === "bottom" ? barSize : 0)
        right: Style.gapsOut + (barPosition === "right" ? barSize : 0)
    }
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "family-lab-requests"
    WlrLayershell.layer: WlrLayer.Top
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
    color: "transparent"
    implicitWidth: Math.min(Style.space(440), screen ? Math.max(200, screen.width - Style.gapsOut * 2) : Style.space(440))
    implicitHeight: Math.min(card.implicitHeight, screen ? Math.max(200, screen.height - Style.gapsOut * 2 - barSize) : card.implicitHeight)
    Flickable {
        id: viewport
        anchors.fill: parent
        contentWidth: width
        contentHeight: card.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        RequestCard {
            id: card
            width: viewport.width
            height: implicitHeight
            request: window.request
            waitingCount: window.waitingCount
            nowSeconds: window.nowSeconds
            busy: window.busy
            errorText: window.errorText
            fontFamily: window.fontFamily
            onActionRequested: function (id, kind, target) {
                window.actionRequested(id, kind, target);
            }
        }
    }
}
