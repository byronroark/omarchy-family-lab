# Architecture

## Components

`scripts/family-lab` contains the prototype session controls, notification transport receiver and desktop watcher. It uses Python’s standard library and external OpenSSH, tmux and installed Omarchy helpers. There is no third-party Python dependency.

- `install`: installs user commands under `~/.local/bin` and creates a generic local JSON config. Refuses to overwrite a different existing installed file.
- `learn`: opens or reattaches a named learning session on a dedicated tmux server (`-L family-lab`, empty initial configuration).
- `stop`: kills that dedicated server and its jobs, disconnecting viewers.
- `view`: forced-command target; attaches read-only to the learning session and ignores SSH_ORIGINAL_COMMAND.
- `ask`: invoked through `ask-dad`; requires a learning session and sends JSON on SSH stdin. No message text enters a remote command.
- `receive <peer-id>`: forced-command target; accepts only a peer configured in the helper’s view mapping. Identity is fixed by the key’s forced argument, never supplied in the payload.
- `watch`: runs in the helper’s graphical login, consumes queued requests and invokes the native notification adapter with a fixed action argv.

Notification payloads are objects with exactly one field, `message`. Limits: 300 printable characters, 2048 input bytes, five-second input deadline, 30-second per-peer cooldown, 20 queued requests and ten-minute delivery expiry. Queue acknowledgement is not a read receipt. Requests are removed after notification submission; they are not durable audit records.

`~/.local/state/family-lab` holds owner-private state. A lock serializes receiver writes and another prevents duplicate watchers. JSON file replacement makes queued writes atomic. The desktop watcher has the helper’s actual D-Bus environment; SSH receivers never manufacture a graphical environment or launch terminals directly.

## Trust boundaries

Notifications authenticate a key, not a human’s current presence. A stolen notification key can submit bounded requests with that key’s peer identity. Source address restrictions and host-key verification complement public-key authentication. No shared HTTP token, internet relay or arbitrary remote action is used.

The receiver executes as the helper’s desktop user. This is an intentionally small prototype, not a fully isolated service. A receiver defect could affect that account. A dedicated receiver identity with carefully permissioned IPC is a future hardening milestone.

The tmux server owner controls its configuration and content. Read-only is an input restriction on the viewing client, not a hostile-user sandbox or guarantee against terminal escape sequence exploits. Keep both sides’ software current. Use the dedicated server only for learning. Other sessions created on that same server may be accessible through client switching, so do not put private work there.

The account’s administrator rights are independent of viewing restrictions. An adult can keep full privileges on their own PC while the helper’s view key remains read-only. Administrator shells and passwords belong in separate unshared terminals. A child’s standard account and a separate parent administrator are a separate machine policy, not enforced by these scripts.

## Desktop adapter

The current adapter expects installed `omarchy-notification-send --exec program arg...` and `omarchy-launch-terminal command arg...`. It relies on actual installed helper behavior, not a generic notification standard guaranteeing clickable actions. Inspect both helpers and test the action on each deployed Omarchy release. The launch target is a configured SSH alias; peer messages are escaped display text only.

No plugin manifest is shipped yet: a placeholder could misleadingly imply loader compatibility. A real plugin needs a supported loader contract, version testing, packaging, visible lifecycle controls and security review first.
