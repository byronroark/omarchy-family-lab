# Staged installation

This is a manual, reviewable prototype installation. Replace angle-bracket placeholders locally. Never commit the completed configuration. Keep local console recovery and an existing administrator connection available while adjusting SSH.

## 1. Inventory and compatibility

Run `bash scripts/preflight.sh` separately on each PC. Its output can contain identifying information; keep it outside this repository and do not paste it into public issues unredacted.

Requirements: Python 3, OpenSSH client/server, tmux, and Omarchy’s existing notification/terminal helpers. Inspect actual installed versions and the package manager’s current help before installing missing dependencies. Do not install a second notification daemon.

Read the files returned by `command -v omarchy-notification-send` and `command -v omarchy-launch-terminal`. The former must support `--exec` with separate command arguments; the latter must forward a command argument vector. Different Omarchy releases may behave differently. Do not modify packaged files under `/usr/share/omarchy`.

**Gate:** recovery works and dependencies/helpers match the documented contract. No Hyprland keybinding, monitor or driver changes are necessary.

## 2. Accounts and LAN policy

Choose a helper desktop account and a local learning account on each learner PC. Learners may retain full administrator privileges on their own computers. For a child-standard-user arrangement, a parent separately audits effective sudo, polkit and Docker access and maintains a separate administrator account. This project does not change privileges.

All participating PCs need SSH servers: helper for notifications; learners for viewing. Choose stable host addresses, such as DHCP reservations. Configure the existing firewall to permit learner-to-helper SSH and helper-to-learner SSH only from intended hosts. Check IPv6 as well as IPv4. No router port forwards, public listeners or UPnP mappings. Guest Wi-Fi isolation may block the workflow.

Inspect the installed sshd service, configuration includes and effective settings. Target key authentication, no remote root login, and no password/keyboard-interactive fallback for the intended accounts after successful key testing. Account expiry and PAM rules must still permit the intended key logins. Do not disable PAM blindly or overwrite unrelated SSH policies.

Before reloading changes, validate `sudo sshd -t` in a local interactive administrator terminal, and inspect `sudo sshd -T -C user=<local-login>,host=<host-name>,addr=<client-address>` for each relevant account. Match configuration, service names and includes to the actual installation. Prove a fresh login before closing existing recovery access.

**Gate:** effective privileges and network exposure match the intended roles; local recovery still works.

## 3. Independent keys and verified hosts

Generate independent Ed25519 keys using `ssh-keygen -t ed25519 -f <new-absolute-key-path> -C <purpose-label>` in the intended user’s terminal. Never overwrite a key or copy private keys between roles.

| Private-key owner | Purpose | Server account |
|---|---|---|
| Helper | Separate read-only view key per learner | That learner’s local account |
| Each learner | Dedicated notification-only key | Helper’s desktop account |
| Authorized administrator, optional | Administration with passphrase | Separate explicitly authorized admin account |

Protect viewing/admin keys with passphrases and a local session agent. Dedicated notification keys may be unattended only when the narrow forced-command restrictions below are applied. Keep `~/.ssh` mode 700 and private keys/config/authorized_keys mode 600, owned by the correct account.

Verify each server’s Ed25519 fingerprint at its physical console with `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`, then compare the first client prompt before enrollment. A key scan alone is not authentication. Scripts require pre-enrolled host keys and strict checking.

Use [SSH alias templates](../examples/ssh-config.example); fill them out only in local `~/.ssh/config`. Inspect `ssh -G <alias>` and avoid conflicting global options, forwarding, or reuse of administrator multiplexed sessions. Different learners have independent host/user/key mappings.

## 4. Install the commands

Review `scripts/family-lab`, then as the intended non-root desktop user on each PC:

```sh
python3 scripts/family-lab install
```

This installs `~/.local/bin/family-lab` and the `ask-dad` symlink, plus `~/.config/family-lab/config.json`. Ensure `~/.local/bin` is on PATH or use absolute paths. The checkout is not needed at runtime.

The helper’s local `view_aliases` maps generic peer IDs to fixed local SSH aliases. The example includes `learner-a` and `learner-b`; remove unused mappings or add a plain ID matching `[A-Za-z][A-Za-z0-9_-]{0,63}`. Each learner sets its own `notify_alias` to its notification connection. Never commit completed mappings.

## 5. Forced authorized_keys entries

Append keys carefully; preserve unrelated entries. For simple absolute home paths without spaces or quotes, a notification public key in the helper account’s authorized_keys looks like:

```text
from="<learner-source-address>",restrict,command="/home/<helper-login>/.local/bin/family-lab receive learner-a" <actual-public-key-line>
```

Each key fixes its peer ID in the forced command. It must exist in the helper’s view mapping. A second learner gets a different key, source address and peer ID. The payload cannot select identity or click destination.

The helper’s viewing public key goes in the corresponding learner account:

```text
from="<helper-source-address>",restrict,pty,command="/home/<learner-login>/.local/bin/family-lab view" <actual-public-key-line>
```

`restrict` disables forwarding, PTY allocation and user rc. Viewing re-enables only PTY allocation with `pty`. The receiver ignores supplied remote commands and never evaluates SSH_ORIGINAL_COMMAND. Confirm the installed OpenSSH supports these key options. Use exact observed source addresses and reviewed IPv4/IPv6 entries. Do not broaden to the whole LAN just to fix a mismatch.

An administrator key belongs in a separately authorized admin account, never in these restricted roles. Audit duplicate key entries: an unrestricted duplicate defeats the intended boundary. A learner administrator may modify their own authorized_keys; they remain in control of their machine.

**Gate:** notification keys cannot allocate a PTY, execute arbitrary commands, use SFTP or forwarding. Viewing keys fail when no learning session exists and cannot obtain an arbitrary shell or forwarding. Test restrictions even when clients request different commands. Inspect effective sshd settings; the presence of a key line alone is not evidence that restrictions work.

## 6. Visible workflow and click acceptance

In the helper’s graphical desktop terminal, load the intended viewing key with `ssh-add <absolute-view-key-path>`, then run:

```sh
family-lab watch
```

No autostart, lingering or background login service is installed. The watcher needs the real graphical D-Bus environment. SSH receivers only queue requests.

In a learner’s normal terminal:

```sh
family-lab learn
```

Inside that learning terminal:

```sh
ask-dad "Could you help explain this?"
```

The helper clicks the notification to open that peer’s configured read-only SSH view. `BatchMode=yes` means the key must already be usable without a password prompt. Manually test `ssh -tt family-learner-a-view` if needed.

Show the learner `tmux -L family-lab list-clients` to inspect attached clients. Helper detaches with Ctrl+B then D. Learner ends sharing with `family-lab stop`, understanding that this ends the server’s running jobs too. Closing or detaching a terminal leaves sharing available. Never rely on logout or suspend to revoke it.

**Gate:** verify the correct learner opens, helper typing/paste cannot control the shell, stop disconnects viewers, and sharing cannot resume until the learner starts it again. Test missing agents, changed/unknown host keys, offline hosts, cooldown, malformed input, stale requests, notification failure, logout and reboot. Record results without identifying data. A working manual SSH view does not prove clickable notifications work.

## 7. Application choices

Steam, AI tutors, coding agents, graphics drivers and other plugins are outside the core installation. Verify their own supported versions, licenses, account eligibility and security boundaries separately. Do not give a child a privileged coding agent or Docker socket; prompts are not parent authentication. Adults can administer their own apps, but should keep privileged work and secrets out of any shared terminal. Do not install unidentified plugin repositories or claim compatibility based only on a name.
