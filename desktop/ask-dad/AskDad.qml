import QtQuick
import Quickshell
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "community.family-lab.ask-dad"
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  BarIconButton {
    id: button
    objectName: "askDadButton"
    anchors.fill: parent
    bar: root.bar
    text: "\uf059"
    slotSize: Style.bar.statusSlot
    fontSize: Style.font.caption
    tooltipText: "Ask Dad"
    Accessible.name: "Ask Dad"
    Accessible.role: Accessible.Button
    onPressed: Quickshell.execDetached(["/usr/local/bin/ask-parent"])
  }
}
