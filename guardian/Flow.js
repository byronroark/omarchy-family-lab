.pragma library

// Presentation only. The policy service, not this JavaScript, owns permission and deadlines.
function parse(raw) {
    var value = JSON.parse(raw)
    if (value.version !== 1 || ["warning", "time-up", "saving", "blocked", "hibernate-error"].indexOf(value.phase) < 0)
        throw new Error("Invalid Dino phase")
    if (typeof value.remaining !== "number" || !isFinite(value.remaining) || value.remaining < 0 || value.remaining > 600)
        throw new Error("Invalid countdown")
    if (typeof value.nextLabel !== "string" || value.nextLabel.length > 160)
        throw new Error("Invalid next-session label")
    if (!Array.isArray(value.helpers) || value.helpers.some(function (x) { return x !== "dad" && x !== "mom" }))
        throw new Error("Invalid helpers")
    return value
}
function countdown(seconds) {
    var n = Math.max(0, Math.ceil(seconds))
    return String(Math.floor(n / 60)) + ":" + (n % 60 < 10 ? "0" : "") + String(n % 60)
}
function permitted(state, action) {
    if (action === "ask-dad" || action === "ask-mom")
        return state.helpers.indexOf(action.slice(4)) >= 0
    if (action === "save") return state.phase === "time-up" && state.remaining > 0
    if (action === "sleep") return ["time-up", "saving", "blocked"].indexOf(state.phase) >= 0
    return false
}
function advance(state, action) {
    if (!permitted(state, action)) throw new Error("Action unavailable")
    var next = JSON.parse(JSON.stringify(state))
    if (action === "save") {
        next.phase = "saving"
        next.remaining = 180 // One explicit save period; unavailable after this transition.
    }
    if (action === "sleep") {
        next.phase = "blocked" // Preview transition only; no power call.
        next.remaining = 0
    }
    return next
}
function tick(state, elapsed) {
    if (typeof elapsed !== "number" || !isFinite(elapsed) || elapsed < 0) throw new Error("Invalid elapsed time")
    var next = JSON.parse(JSON.stringify(state))
    next.remaining = Math.max(0, next.remaining - elapsed)
    if ((next.phase === "saving" || next.phase === "time-up") && next.remaining === 0) next.phase = "blocked"
    return next
}

// Synthetic resume fixture only. A trusted wake event must own this in production.
// Staying blocked never restores the desktop or creates another save grant.
function wakeBlocked(state) {
    var next = JSON.parse(JSON.stringify(state))
    next.phase = "blocked"
    next.remaining = 300
    return next
}
