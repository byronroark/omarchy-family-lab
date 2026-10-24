import QtQuick
import Quickshell
import qs.Ui

BarWidget {
    id: root
    moduleName: "community.family-lab.manager"
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight

    // Fixed local application only; no policy operations or administrator keys.
    function openManager() {
        Quickshell.execDetached([Quickshell.env("HOME") + "/.local/bin/family-time-widget"])
    }
    function triggerPress(buttonCode) {
        if (buttonCode === Qt.LeftButton) root.openManager()
    }
    BarIconButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "\uf0c0"
        tooltipText: "Family Manager - breaks and bedtime"
        onPressed: function(buttonCode) {
            if (buttonCode === Qt.LeftButton) root.openManager()
        }
    }
}
