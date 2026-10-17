import QtQuick

Canvas {
    id: dino
    property bool sleepy: false
    implicitWidth: 160
    implicitHeight: 160
    Accessible.name: sleepy ? "Sleepy baby dinosaur" : "Baby dinosaur with tiny arms"
    onSleepyChanged: requestPaint()
    onPaint: {
        const c = getContext("2d")
        c.clearRect(0, 0, width, height)
        // Original code-drawn mascot, with no downloaded assets or external fonts.
        const rows = ["      KKKKKK    ", "     KGGGGGGK   ", "     KGWWGGGK   ",
                      sleepy ? "     KGKKGGGK   " : "     KGWKGGGK   ",
                      "     KGGGKKKK   ", " K   KGGGGGK    ", "KGK KGGGKKK     ",
                      "KGGKGGGGGKK    ", " KGGGGGGGKGK   ", "  KGGGGGGKK    ",
                      "   KGGGGGK     ", "   KGGGGGK     ", "   KGKKG K     ",
                      "  KGGK KGGK    ", "  KKKK KKKK    "]
        const unit = Math.floor(Math.min(width / 16, height / 15))
        const x = Math.floor((width - unit * 16) / 2)
        const y = Math.floor((height - unit * 15) / 2)
        const palette = {"K": "#264b40", "G": "#80c7a3", "W": "#f3fff8"}
        for (let r = 0; r < rows.length; r++) {
            for (let col = 0; col < rows[r].length; col++) {
                let color = palette[rows[r][col]]
                if (color) { c.fillStyle = color; c.fillRect(x + col * unit, y + r * unit, unit, unit) }
            }
        }
    }
}
