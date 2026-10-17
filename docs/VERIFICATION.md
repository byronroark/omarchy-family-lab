# Verification status

The current prototype was checked against locally installed Omarchy helper source. That notification helper accepts an argument-vector click command through `--exec`; the terminal helper forwards a command vector through its desktop terminal launcher. This is evidence about inspected source, not a guarantee across Omarchy releases.

Local tests exercise Python/shell syntax, installation into a temporary home, configured peer identity, cooldown, literal message handling, malformed/oversize payload rejection and private queue permissions. A real isolated tmux test checks the read-only client flag and disconnection on server shutdown. The local tmux version tested during initial prototype development was 3.7c. The consented-control test additionally exercises pending read-only input, local/SSH/piped approval guards, decline, single-connection admission, stale confirmation rejection, pending expiry, ordinary viewers remaining read-only, actual approved command execution, red status, learner shortcut revoke during a foreground job, reconnect approval, grant expiry, abrupt supervisor death and stop. It runs on an isolated temporary home/socket and uses Linux-specific process/clock features. CI runs basic checks on Linux; it does not run an Omarchy graphical desktop.

Routing tests cover direct Dad/Mom selection, legacy Dad-only fallback, scoped relay source/learner identity, original expiry, deduplicated retries after a simulated lost acknowledgement, replay/conflict rejection, one-hop loop prevention, literal text and fixed notification/menu actions. GUI/native notification calls are mocked and relay endpoints are local subprocesses: this does not verify actual desktop clicks or authenticated SSH across hosts. Named helper control status is covered by the real isolated tmux test.

The installed Zenity help was checked for extra buttons and plain-text question dialogs. The inspected Omarchy notification service invokes the native command/default action and its card does not render extra action buttons, so routing uses a click-through menu.

No supported release or full multi-PC acceptance result is claimed. SSH restrictions, authenticated transport across real hosts, notification click behavior, sleep/logout/reboot and application privileges require deployment-specific checks.

## Deployment acceptance template

Record sanitized pass/fail/version results, never hostnames, usernames, fingerprints, LAN addresses or logs containing personal information.

| Gate | Status |
|---|---|
| Local recovery and intended account privileges | Pending |
| Host-key verification and correct independent keys | Pending |
| Forced commands; shell/SFTP/PTY/forwarding negative tests | Pending |
| Correct configured peer and notification click target | Pending |
| Read-only view and deliberate stop/disconnect | Pending |
| Detach/close semantics understood | Pending |
| Offline, stale queue, cooldown and malformed input | Pending |
| Agent failure, changed host keys, logout/reboot | Pending |
| Actual Omarchy/helper/terminal version compatibility | Pending |
| Direct Dad/Mom destination keys and watchers | Pending |
| Click menu and Ask Mom relay over actual SSH | Pending |
| Relay identity, original expiry, failure/retry on deployed PCs | Pending |
| Optional control key restrictions and correct peer | Pending |
| Local consent, visible status, revoke during foreground work | Pending on deployed PCs |
| Expiry, reconnect, supervisor failure, suspend/resume | Pending on deployed PCs |

## Primary references

- [Omarchy source](https://github.com/omacom/omarchy) and [notification helper](https://github.com/omacom/omarchy/blob/master/bin/omarchy-notification-send): always compare actual installed source.
- [OpenSSH authorized_keys manual](https://man.openbsd.org/sshd.8), [server configuration](https://man.openbsd.org/sshd_config.5), and [client configuration](https://man.openbsd.org/ssh_config.5): validate effective local policy.
- [Upstream tmux manual](https://github.com/tmux/tmux/blob/master/tmux.1): dedicated server socket and read-only attach.
- [Linux parent-death signals](https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html): client cleanup on unexpected supervisor exit.
- [Zenity upstream source](https://github.com/GNOME/zenity): question dialogs and extra-button behavior; validate installed options and GUI behavior.
- [Desktop notifications specification](https://specifications.freedesktop.org/notification/latest-single/): action support varies by server; the prototype uses a native Omarchy-specific adapter.

No official plugin compatibility is claimed until a real plugin is packaged and tested against a declared supported loader/API version.
