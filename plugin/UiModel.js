.pragma library

// A narrow local data contract, never a command supplied by a peer.
function parse(raw) {
    var data = JSON.parse(raw)
    if (data.version !== 1 || typeof data.enabled !== "boolean" || typeof data.paused !== "boolean" || !Array.isArray(data.requests) || data.requests.length > 20)
        throw new Error("Unsupported Family Lab UI state")
    for (var i = 0; i < data.requests.length; i++) {
        var row = data.requests[i]
        if (!/^[a-f0-9]{32}$/.test(row.id) || typeof row.peer !== "string" || typeof row.message !== "string" || row.message.length > 600 || typeof row.via !== "string" || typeof row.expires !== "number" || !isFinite(row.expires) || !Array.isArray(row.actions))
            throw new Error("Invalid request card")
        if (row.name !== undefined && (typeof row.name !== "string" || row.name.length > 256))
            throw new Error("Invalid display name")
        for (var j = 0; j < row.actions.length; j++) {
            var action = row.actions[j]
            if (typeof action.label !== "string" || !commandFor("family-lab", row.id, action.kind, action.target || ""))
                throw new Error("Invalid card action")
        }
    }
    if (!data.enabled || data.paused) data.requests = []
    return data
}

function commandFor(binary, id, kind, target) {
    if (!/^[a-f0-9]{32}$/.test(id)) return null
    if ((kind === "open" || kind === "dismiss") && !target)
        return [binary, "ui-action", id, kind]
    if (kind === "forward" && /^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(target))
        return [binary, "ui-action", id, kind, target]
    return null
}
