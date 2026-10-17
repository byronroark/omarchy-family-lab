# Operations and recovery

## A normal session

Helper starts the visible watcher and loads the appropriate viewing key into their local agent. Learner starts `family-lab learn`, does only agreed learning work, and uses `ask-dad "message"` or `ask-mom "message"` to select the helper. Helper clicks the notification, opens the terminal directly or through the routing menu, explains what they see and suggests steps. If Dad is busy, **Ask Mom** in that menu forwards the request using the separately enrolled route; it never approves control. See [ROUTING.md](ROUTING.md). The learner types the commands by default. For agreed hands-on assistance, use the separate [consented control workflow](CONTROL.md): helper requests, learner approves locally, red status shows writable control, and Ctrl+B then Ctrl+R revokes it.

For an adult administrator, system changes can be made in their own separate unshared terminal. Helper admin work uses only a separate explicitly authorized account/key. For a child standard account, a parent performs agreed admin tasks separately. Never weaken viewing-key restrictions to make typing easier; optional control has a different key and consent path.

Learner runs `family-lab stop` when finished. This kills the dedicated server and its jobs. Closing a terminal and Ctrl+B D merely detach. Helper closes the viewer and stops the watcher with Ctrl+C.

## Troubleshooting

| Symptom | Response |
|---|---|
| Command missing | Check `~/.local/bin` on PATH or use the absolute path; do not reinstall as root. |
| No learning session | Learner explicitly starts `family-lab learn`. Requests do not start sharing silently. |
| Request rejected | Check the peer mapping, bounded single-line payload and 30-second cooldown. |
| Queued, no notification | Helper must have watcher running inside their actual graphical login. Inspect its errors and desktop notification/do-not-disturb settings. Queue acknowledgement is not a read receipt. |
| Click fails | Inspect installed helper support; test the configured SSH alias, key agent and active learning session. Do not disable host checking. |
| Permission denied | Check key/account, ownership/modes, source-address restriction, effective sshd Match rules, expiry and agent. Authorized administrator can inspect local sshd logs privately. |
| Host key changed | Stop and compare at the physical console. Investigate address reuse/reinstallation before changing known_hosts. |
| Timeout | Check power/suspend, addresses, route, Wi-Fi isolation, sshd and IPv4/IPv6 firewall rules. No router forwarding. |
| Wrong peer opens | Stop watcher; inspect fixed receive arguments and view_aliases. Each target must map to the intended host/account/key. |
| Ask Mom / relay fails | Check the separate direct or relay key, Mom’s watcher, source/learner allowlist and viewing map. Use `family-lab inbox` to find the still-live original request and retry a configured route. Acknowledgement is not a read receipt. |
| No Ask Mom button | Forwarding needs an explicitly enrolled route and Zenity. The native toast opens a menu; it does not render multiple inline buttons. |
| Control request/approval fails | Check the separate control alias/key, active learning session, pending connection, local interactive confirmation and installed versions. Do not repurpose a viewing key. |
| Ordinary viewer controls shell | Stop sharing immediately. Audit actual key used, forced command, unrestricted duplicates and read-only attach. Re-run negative tests. |
| Still shareable after closing | Closing/detaching is not revocation. Learner runs `family-lab stop` from another local terminal in the same account. |
| Queue full | Restore watcher; stale entries expire on processing. Inspect/remove only confirmed old request files locally. Contact each other directly while unavailable. |

Never upload raw logs or inventories to a public issue. If using Omarchy diagnostics, inspect the installed command help and use `omarchy debug --no-sudo --print` where supported; redact locally. Configuration reset commands are not required by this project.

## Maintenance

Keep OS, terminal, SSH and tmux updated, with local recovery and backups. Re-run acceptance after changes to SSH policy, accounts, addresses, terminal helpers or Omarchy versions. Keep an offline private record of key fingerprints, host enrollment and actual configuration. No record belongs in this public checkout.

Back up learning files and necessary local config securely. The prototype does not record terminal sessions or maintain a durable message history. Private live help records are retained for up to ten-minute action validity and pruned on command activity; state files can remain while all commands are stopped. Other applications may log independently.

## Revoke or uninstall

For control-only revocation use `family-lab revoke-control` or the learner shortcut; remove the separate control key to disable future requests. Review partial commands and already-started jobs: revocation does not undo them. Stop the learning server and watcher. Remove the affected public-key line to prevent new logins; established connections need explicit termination, including stopping the dedicated server. Rotate a lost key and recheck its restrictions. Do not delete an entire authorized_keys file.

To remove the project, stop all sessions first, remove only its installed user commands, inspect and remove only its local config/state if desired, remove its SSH aliases/keys and reverse only dedicated firewall changes. Preserve unrelated SSH/admin access and user files. No application, desktop reset or account deletion is needed.
