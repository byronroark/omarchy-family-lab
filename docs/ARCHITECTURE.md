# Architecture

## Components

`scripts/family-lab` contains the prototype session controls, notification transport receiver and desktop watcher. It uses Python’s standard library and external OpenSSH, tmux and installed Omarchy helpers. There is no third-party Python dependency.

- `install`: installs user commands under `~/.local/bin` and creates a generic local JSON config. Refuses to overwrite a different existing installed file.
- `learn`: opens or reattaches a named learning session on a dedicated tmux server (`-L family-lab`, empty initial configuration).
- `stop`: kills that dedicated server and its jobs, disconnecting viewers.
- `assist <peer-id>`: helper command using an optional separately enrolled control alias/key.
- `control`: forced-command target; one supervised read-only client waits for connection-specific local consent, then receives at most five minutes of writable input.
- `allow-control [seconds]`: local interactive warning/confirmation, bound to the exact pending request; no blanket/reusable grant.
- `revoke-control`: removes input permission and detaches the registered controller, keeping ordinary viewers and learning jobs. Also bound to Ctrl+B then Ctrl+R only in the learning tmux server.
- `view`: forced-command target; attaches read-only to the learning session and ignores SSH_ORIGINAL_COMMAND.
- `ask`: invoked through `ask-dad`, `ask-mom` or `family-lab ask HELPER MESSAGE`; selects an explicitly enrolled destination, requires a learning session and sends JSON on SSH stdin. No message text enters a remote command.
- `receive <peer-id>`: forced-command target; accepts only a peer configured in the helper’s view mapping. Identity is fixed by the key’s forced argument, never supplied in the payload.
- `receive-forward SOURCE PEER`: relay endpoint fixing both identities in the key’s forced command, checked against the receiving helper’s explicit allowlist and viewing map.
- `forward ID HELPER`: forwards a locally stored, live, original request on a configured source/learner-scoped SSH route; no key, control grant or privileged operation is sent.
- `request ID`: opens a local action menu with fixed Open terminal/Ask helper/Close choices.
- `inbox`: lists live request IDs and routing status without message bodies.
- `watch`: runs in the helper’s graphical login, consumes queued requests and invokes the native notification adapter with a fixed action argv.

Direct notification payloads have exactly one field, `message`. Relay payloads have exactly `id`, `message`, `time`, and `expires`; source and learner come only from the enrolled forced command. Limits: 300 printable characters, 2048 input bytes, five-second input deadline, 30-second cooldown per direct peer or source/peer relay, 20 live inbox records, and ten-minute original expiry. Queue acknowledgement is not a read receipt. Queue entries are removed after notification submission, while private request records remain available for click actions until expiry. Pruning runs on command activity, so expired files can remain while every process is stopped. These are not durable audit records.

`~/.local/state/family-lab` holds owner-private state. A lock serializes receiver writes and another prevents duplicate watchers. JSON file replacement makes queued writes atomic. The desktop watcher has the helper’s actual D-Bus environment; SSH receivers never manufacture a graphical environment or launch terminals directly.

## Trust boundaries

Notifications authenticate a key, not a human’s current presence. A stolen notification key can submit bounded requests with that key’s peer identity. Source address restrictions and host-key verification complement public-key authentication. No shared HTTP token, internet relay or arbitrary remote action is used. A forwarded request is the authenticated helper’s attestation of the original learner, explicitly displayed as such; it is not a fresh direct learner signature. One-hop forwarding, preserved expiry/ID, scoped routes and duplicate/conflict checks bound relay behavior. See [ROUTING.md](ROUTING.md).

The receiver executes as the helper’s desktop user. This is an intentionally small prototype, not a fully isolated service. A receiver defect could affect that account. A dedicated receiver identity with carefully permissioned IPC is a future hardening milestone.

The tmux server owner controls its configuration and content. Read-only is an input restriction on the viewing client, not a hostile-user sandbox or guarantee against terminal escape sequence exploits. Keep both sides’ software current. Use the dedicated server only for learning. Other sessions created on that same server may be accessible through client switching, so do not put private work there.

For optional control, a private request record is serialized under a state lock and a separate lifetime lock admits only one connection. The supervisor tracks the tmux client PID/name, Linux process start time and boot identity. It enables the red indicator before toggling that client writable. A boot-time clock includes suspend; pending requests expire after 60 seconds and approval is at most 300 seconds. Normal revoke removes input permission before detach; Linux PR_SET_PDEATHSIG kills the client on supervisor death. A new connection always needs new consent. [Control details and limits](CONTROL.md) explain why approved shell access is a trust boundary, not a sandbox.

The account’s administrator rights are independent of viewing restrictions. An adult can keep full privileges on their own PC while the helper’s view key remains read-only. Administrator shells and passwords belong in separate unshared terminals. A child’s standard account and a separate parent administrator are a separate machine policy, not enforced by these scripts.

## Desktop adapter

The current adapter expects installed `omarchy-notification-send --exec program arg...` and `omarchy-launch-terminal command arg...`. It relies on actual installed helper behavior, not a generic notification standard guaranteeing clickable actions. Inspect both helpers and test the action on each deployed Omarchy release. The launch target is a configured SSH alias or a fixed local `request` action with an opaque stored ID; peer messages are escaped display text only. Inspected native notification cards expose one click command, so the routing adapter opens a Zenity question menu using inspected command options for extra helper choices instead of claiming unsupported inline buttons. The GUI adapter invokes fixed action functions; a future plugin can present those same operations with its own reviewed UI.

No plugin manifest is shipped yet: a placeholder could misleadingly imply loader compatibility. A real plugin needs a supported loader contract, version testing, packaging, visible lifecycle controls and security review first.
