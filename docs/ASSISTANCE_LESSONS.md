# Assistance implementation and verification record

This record describes the family assistance work incorporated on 18 October 2026. It intentionally excludes household identities, IPs, keys, request IDs, logs and screenshots. PRs #5 and #6 were merged first; their optional policy/Dino features remain separately gated and are not activated by enrollment.

## Implemented and observed on the two-PC lab

| Capability | Observed result |
|---|---|
| Separate administrator SSH | Encrypted Ed25519 identity; interactive admin authentication stays private |
| Ask Dad requests | Child normal-account request, Dad graphical watcher and persistent action panel |
| Read-only learning view | Existing tmux learning session visible; typing has no effect |
| Help together | Explicit per-connection child consent, visible typing, `stop-dad` revocation; learning session survives |
| Admin demonstration | Separate root tmux server and locked viewer UID with server-enforced read-only access; viewer opens on child desktop and closes when parent exits |
| Widget | Native GTK prompt, genuine placeholder, topic selection, PNG clipboard and Capture region preview; message and image delivered |
| Bar shortcut | Question-mark icon opens the same widget near the top-right below the bar |
| Package approval | Repository package request approved to completion, then a fresh request denied with child-visible result |
| Gaming approval | Lutris denied, then approved on a new request; actual installation completed and the child saw the application open |
| Parent-managed update | Completed from separate administrator account; reviewed child migrations completed without restoring child sudo; assistance worked after reboot |

These observations validate the individual deployed paths, not a fresh run of the newly assembled enrollment script. Later repository fixes and the configurable-port support are covered by isolated tests; they have not all been redeployed to the existing lab.

## Lessons encoded in the implementation

- Use separate help and administration identities. A help request never grants sudo; child consent to typing only controls the learning account. Do not put an administrator shell into the learner-owned tmux server.
- Normalize terminal type to `xterm-256color` for remote launches. An absent `xterm-ghostty` terminfo entry caused the initial attach failure.
- Native notification banners were easy to miss. The parent’s GTK action panel remains open until a choice; software requests expire after 15 minutes, ordinary help after one day.
- Give consent waiting enough time to walk between desks: ten-minute request wait, five-minute grant. Repeated Allow must not extend the original grant. Supervise the tmux client so revoke, expiry or lost supervisor disconnects only that client.
- tmux 3.7’s server-enforced cross-UID read-only access rejects a redundant `attach -r` in this deployment. The locked viewer uses the server ACL without that redundant flag. Same-UID learning watch still uses `-r`; that is a trusted-helper convention, not a boundary against a compromised learner account.
- Import GUI environment from the intended user manager; an administrator SSH shell does not represent the child’s Wayland session. Child GUI launches run as the child with no new privileges, clean environment and no parent SSH agent.
- Region capture hides the request popup and holds the GTK application alive. Avoid waiting on inherited clipboard-helper pipes; consume the bounded PNG after the capture helper exits. Strip metadata, reject malformed/animated/oversized payloads, bind fetched screenshots to request hashes and cap cached images.
- Run the stock updater as the separate normal administrator. A root demonstration is the wrong environment. Use a private transcript rather than a shared `/tmp` filename; updater migration markers are per-user even when package/kernel work is machine-wide.
- Child migrations need classification and source hashes. Reuse reviewed system work already completed by the parent, run personal configuration without privilege, split mixed browser steps, and stop on new/changed migrations. A no-op migration run now reports no new audit file instead of naming one it never created.
- Software approval needs a private parent-owned snapshot, not mutable child request state. Validate exact schemas, reject flags/files/commands/AUR build requests, make decisions one-shot, and separate public status from private root audit records. A disconnected view must not casually replay an installation.
- Menu text is not a root command. Resolve fixed menu IDs through a root-owned reviewed catalog, hash-check source helpers, execute fixed package operations, and drop to the learner for personal configuration. Unknown or changed helpers need manual parent review.
- Controller support is exceptional: adding the `input` group grants raw input access. Disclose it before approval; the installer does not grant it during enrollment, and subsequent standard-account checks will flag it.
- Backups and idempotence are essential, but setup is not an atomic transaction across two machines. Preserve console recovery, stop on local drift, and describe partial failures accurately.

## Source map

| Path | Responsibility |
|---|---|
| `master-installation.sh`, `setup/` | Interactive private enrollment, plan, verified host pinning, restricted role keys, managed writes/backups and verification |
| `assistance/family-help-child` | Bounded requests, forced polling/view/control endpoints, consent and child GUI watcher |
| `assistance/family-help-dad` | Fixed enrolled polling, request validation and private action launches |
| `assistance/family-help-widget`, `family_help_image.py` | Native child/parent panels and bounded PNG handling |
| `assistance/family-admin-demo` | Short-lived root demonstration, tmux UID ACL and fixed viewer |
| `assistance/family_software.py`, `family-software-*` | Typed software requests, private parent review, one-shot root execution and statuses |
| `assistance/family_menu.py`, `family-menu-*` | Reviewed menu catalog, source checks, fixed package and child configuration phases |
| `assistance/family-update`, `family-migrate-child`, `reviewed-migrations.json` | Normal-admin update orchestration and reviewed child migrations |
| `desktop/ask-dad/`, `assistance/family-help-desktop-setup` | Learner bar icon and narrowly scoped popup position rule |

## Remaining acceptance and limits

- Clean-machine two-PC enrollment from the master script, failure recovery on those machines and repeated live upgrade runs remain to be tested. Isolated tests cannot validate a distro’s effective PAM, SSH and GUI behavior together.
- The new software **update request** broker route, every default agent, controller changes and each manual-review branch have not all been tested end to end. Parent-managed updates and Lutris/package approve/deny have been tested separately.
- The menu catalog targets inspected 4.0.5 helper sources. It is not automatic compatibility with all future Omarchy releases. Hash mismatch downgrades to manual review; reviewed migrations also require maintenance.
- Agent downloads and application installation remain deliberate parent choices. Fixed approved package transactions may execute distribution package hooks as root. The child configuration phase has user-level capabilities, not an application sandbox.
- Second-helper enrollment/GUI management and simultaneous multiple-learner queues, broader polkit/container/device auditing, unattended approvals, and arbitrary terminal-sudo interception are not implemented. Terminal admin tasks use the private parent workflow.
- Experimental reporting, policy/PAM, time enforcement and Dino modules are not enabled by this installer. Their merged code still requires its own deployment acceptance.

See [ENROLLMENT.md](ENROLLMENT.md) for the reproducible setup and the live checklist; see [SECURITY.md](../SECURITY.md) before relying on the boundaries.

## Configurable primary helper follow-up

Enrollment now asks for Dad, Mom, or another parent/guardian and a child-facing display name. Mom can be the sole technical helper without a Dad account or device. Widget text, question placeholder, consent/status messages, menu descriptions, application name and tray tooltip follow this setting. Role-specific and neutral command aliases map to the single selected helper; administrator authentication remains separate. Legacy Dad configurations remain readable. These changes have automated Mom/guardian configuration, UI and compatibility coverage; a live Mom enrollment has not yet been performed.
