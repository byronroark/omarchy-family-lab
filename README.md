# Omarchy Family Lab

Visible, consent-based terminal assistance for Omarchy PCs on a trusted local network.

**Experimental community project.** Not an official Omarchy plugin, not affiliated with or endorsed by the Omarchy maintainers, and not yet validated as a complete multi-PC deployment. The current implementation is a small command-line prototype; a shell plugin is a future milestone.

## What it does

- A learner starts a dedicated tmux learning terminal.
- `ask-dad "Could you help explain this?"` submits a bounded message over authenticated SSH.
- The helper receives an Omarchy desktop notification with an action to open that learner’s terminal.
- A separate restricted viewing key attaches read-only. The learner can end sharing and disconnect viewers.
- Optional [consented control](docs/CONTROL.md) uses another key, local approval for each connection, a red status indicator, a five-minute maximum grant and a learner revoke shortcut.

Roles describe a workflow, not privileges or family relationships. A learner can be an independent adult administrator or a standard user. A child’s account can remain unprivileged while an adult owns a separate administrator account. Administrator access is separate from this project’s read-only assistance path.

```text
Learner PC ── dedicated notification key ──> helper SSH forced receiver
                                                  |
                                           private bounded queue
                                                  |
                                     watcher in graphical desktop
                                                  |
                                        clickable notification
                                                  |
Helper PC ── separate read-only viewing key ──> learner learning terminal
```

Each learner uses a generic configured peer ID such as `learner-a`. Multiple learners can use separate PCs, accounts and keys. Actual addresses, usernames, host fingerprints and private keys stay on those PCs, outside this repository.

## Start here

1. Read [security boundaries](SECURITY.md) and [architecture](docs/ARCHITECTURE.md).
2. Follow the [staged installation guide](docs/INSTALL.md), stopping at each acceptance gate.
3. Use the [operations guide](docs/OPERATIONS.md) for normal sessions, recovery and removal.
4. For optional hands-on help, read [consented control](docs/CONTROL.md) and enroll a separate control key.
5. Check [verification status](docs/VERIFICATION.md) before relying on any capability.

No curl-to-shell installer, automatic account creation, driver changes, firewall edits or SSH policy changes are provided. Do not run the user installer as root. No default keyboard shortcuts or monitor layouts are changed.

**Control remains opt-in.** The notification always opens read-only. Helper requests control with `family-lab assist learner-a`; learner approves locally with `family-lab allow-control`. Ctrl+B then Ctrl+R revokes control without ending the learning session. Control gives a trusted helper the learning account’s shell capabilities; it is not a sandbox.

**Closing or detaching the terminal does not end sharing.** `family-lab stop` ends the dedicated tmux server, disconnects viewers and ends its running jobs. Never type secrets or perform privileged work in a shared terminal.

## Development and plugin direction

See [contributing](CONTRIBUTING.md) and the [roadmap](docs/ROADMAP.md). Transport and session logic stay separate from the desktop adapter so a future shell plugin can provide visible sharing status and request controls without handling admin credentials.

Published material must contain synthetic examples only. Never contribute private keys, personal configuration, household details, logs, chat transcripts, screenshots with personal information, or hardware inventories.

MIT licensed. No official compatibility or security certification is implied.
