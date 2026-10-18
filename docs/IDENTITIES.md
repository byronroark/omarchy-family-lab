# Configurable learner IDs and private display names

`learner-a` is only a synthetic example, never a required value. The stable peer ID can already be any plain value matching `[A-Za-z][A-Za-z0-9_-]{0,63}`, such as `alex`, `sam`, or `study-pc`. It is fixed by the enrolled key's forced receiver command and local route mappings, not supplied by an incoming message. Do not rename only one occurrence: update the corresponding forced commands, view/control/report/policy mappings and any relay routes together.

A separate helper-local `peer_labels` map now allows readable names with spaces and Unicode. Synthetic example, merged into each parent's existing private `~/.config/family-lab/config.json`:

```json
"peer_labels": {
  "study-pc": "Alex Rivera",
  "learner-b": "Example Adult"
}
```

Native notifications, routing menus and inline cards show `Alex Rivera (study-pc)`. Keeping the stable ID visible disambiguates duplicate names/devices. Labels are 1-80 printable characters; control characters/newlines are rejected. Inline text is plain text, never executable markup. Both old UI data without a name and configs without labels retain the original ID fallback. Labels do not change key identity, routing, approval or privileges.

Mom and Dad each control their own labels. A forwarded request preserves its enrolled stable ID; the receiving parent supplies their own local label. The child's incoming payload cannot choose a different display name. Multiple queued requests remain distinct by request ID, with the oldest visible card and a waiting count; this change does not add a multi-card dashboard.

Using a person's name as the peer ID makes that name part of the private LAN protocol, local logs and key configuration. A generic stable ID plus a local display name avoids needing to rename routes when a display preference changes. Either choice is supported. Real names and completed mappings belong only on household PCs, never in public examples, screenshots, tests or reports committed to Git.

Parent menu policy names are independently stored in each enrolled subject’s `name` field. Assistance-card names come from the helper-local `peer_labels` map; changing one does not silently change the other. Use the same preferred name in both if desired.
