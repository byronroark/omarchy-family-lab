# Reusable enrollment for the verified Ask Dad workflow

This is the polling workflow implemented in `assistance/`, with a native GTK request widget, screenshots, a top-right bar icon, consented typing, an independently authenticated admin demonstration, and named software approvals. Dad connects to the learner; Dad does **not** need an SSH server. Mom’s login and address can be recorded, but her access/UI is deliberately deferred.

The older `scripts/family-lab` push transport, forwarding and inline QML card are separate prototypes. Do not complete the old manual/PDF instructions over this installation: their `ask-dad` aliases and SSH transport differ. This installer stops at conflicting user command aliases rather than silently replacing them.

## Status and prerequisites

The individual assistance functions were tested on two actual Omarchy PCs. The new enrollment orchestrator is tested in isolated file trees and mocked enrollment calls; **a clean-machine, two-PC rollout using this master script has not yet been performed**. Keep recovery access and review the plan. No test here certifies the whole machine’s security.

Before enrollment, prepare existing Omarchy installations with:

- A standard learner account and a separate, working parent administrator in `wheel`. The installer does not create or modify these human accounts, remove privileges, or fix existing running processes with stale groups. Audit sudo, polkit, containers and devices first.
- Working private administrator SSH access from Dad, using a passphrase-protected OpenSSH Ed25519 key. Keep that key on Dad’s PC. Use a local SSH agent or enter its passphrase in the private terminal.
- Stable LAN IP addresses, the learner’s existing SSH server, and deliberate LAN firewall rules. No router forwarding. The installer neither enables SSH nor changes the firewall or broad authentication rules.
- Python 3 with PyGObject, GTK 4 and GdkPixbuf; tmux with `server-access`; OpenSSH; `setpriv`; `setfacl`; normal Omarchy notification, terminal, screenshot, menu, shell/plugin and Lua Hyprland helpers. This targets the inspected Omarchy 4.0 Lua/plugin API. Stop and inspect incompatible releases.
- The learner logged into their graphical desktop when using `--activate`. No package operation or pending manual system repair should be underway.

At the learner’s physical console, inspect the host fingerprint:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

A network key scan is accepted only when it matches that independently verified fingerprint.

## 1. Configure and review on Dad’s PC

Review this repository and run from its root, as Dad’s normal desktop login:

```sh
./master-installation.sh configure
./master-installation.sh plan
```

The interactive prompts ask for a stable learner ID, child login/display label/IP/SSH port, parent administrator login/key path, Dad login/IP, and optional deferred Mom login/IP. Nothing hardcodes a particular child or machine.

The private profile defaults to `~/.config/family-help/setup.json` (mode 600). Use `--profile /absolute/private/path.json` consistently for another location. Profiles and enrollment bundles must stay outside the checkout. `plan` reads the profile and prints proposed actions; it makes no system changes or network connections. With no command the script selects `plan`.

## 2. Enroll the helper and create a bundle

```sh
./master-installation.sh apply
./master-installation.sh bundle --out "$HOME/.local/state/family-help/enrollment-bundle"
```

Helper apply verifies the host fingerprint, creates three independent restricted-role Ed25519 keys, installs the local watcher/programs, and writes a dedicated SSH configuration. These unattended keys are for polling, read-only viewing and consented typing only. Administrator access retains its separate encrypted key and private interactive authentication. No SSH agent or forwarding is exposed to the child.

The bundle contains the reviewed source, public role keys and private enrollment configuration. It contains **no private keys, logs or Git history**. Keep it private because it still contains family login names and addresses. Existing bundle directories are never overwritten; choose a new destination for another bundle.

The current helper UI supports **one learner enrollment per desktop profile**. IDs and device settings are reusable; simultaneous multiple-child queues and Mom enrollment are future work. Existing enrollment with a different learner ID is refused.

## 3. Copy and apply on the learner using the parent account

Use the administrator SSH alias you already verified. Here `learner-admin` is an example alias, not one the installer creates. Copy to a new directory that contains only this bundle:

```sh
scp -r "$HOME/.local/state/family-help/enrollment-bundle" learner-admin:family-enrollment-bundle
ssh -t learner-admin
```

In that separate administrator SSH shell:

```sh
cd ~/family-enrollment-bundle
sudo ./master-installation.sh apply --role learner --profile "$PWD/enrollment.json" --activate
sudo ./master-installation.sh verify --role learner --profile "$PWD/enrollment.json"
```

Enter the administrator password privately. The bundle must match this PC’s host key. The installer checks the child’s groups/sudo policy, creates or verifies the locked `familyviewer` system identity, installs root-owned helpers/configuration, and checks both SSH syntax and the **effective** viewer Match policy before reloading the existing SSH service. `familyviewer` is not an administrator: its forced command can only view the root demonstration through tmux’s server-enforced read-only UID rule.

Child SSH entries, menu overrides, viewer key and desktop configuration run **as the child**, with a clean environment and `NoNewPrivileges`. Existing unrelated keys and menu entries are preserved. The learner’s viewer private key is generated on that PC and can only reach the forced loopback viewer role. For a custom SSH port, its loopback host pin and connection use that port too.

Without `--activate`, services are enabled for the next graphical login; rerun with `--activate` once logged in to install/enable the tray icon immediately. Activation requires working desktop APIs and refuses existing Hyprland errors. It backs up and restores the files it changes if compositor/plugin validation fails. No keyboard shortcuts or monitor layout are changed.

Back on Dad’s PC:

```sh
./master-installation.sh apply --activate
./master-installation.sh verify
```

`verify` checks local configuration and effective SSH settings, not delivery of a real request. Complete the acceptance checks below.

## Repeat runs, upgrades and recovery

Unchanged managed files are left untouched. Root and helper managed-file state plus private before-images live respectively in `/var/lib/family-help-install/` and `~/.local/state/family-help-install/`. Existing unmanaged or locally edited managed files cause a stop. Review the files and backups before deliberately using `--adopt-existing`; it is an explicit migration/upgrade option, not a permission repair tool.

Root/helper file transactions roll back their changed managed files on failure. Account creation, generated keys, directories, child-owned menu/key updates, service actions and all desktop side effects are **not** one atomic cross-machine transaction. A failure can leave partial enrollment; inspect the error, preserve recovery access and rerun after resolving it. Do not claim that a failed setup did nothing. Backups are private and are not uploaded.

The child menu merge makes a first-run `.before-family-setup` backup. The desktop adapter separately makes `.before-family-help` backups. Restore deliberately while logged into the intended account; do not replace a whole SSH configuration from an old backup without inspecting unrelated access. No automatic uninstall removes human accounts, keys, PAM hooks, applications or system settings.

For removal, first stop/disable the two graphical user services and remove only their managed enable links. Remove the marked `family-help managed keys` block from the child’s `authorized_keys` to prevent new help connections. End any active assistance/demo explicitly. Restore the backed-up menu and managed Hyprland block/plugin only after checking for newer personal changes. Validate `sshd -t` before removing/reloading the dedicated viewer drop-in. Keep the administrator recovery connection open. Root helpers may be removed only after all their callers are disabled; delete the locked viewer account last if it is unused. Revoke role keys on both sides, then delete private bundles/backups according to your own retention needs. There is intentionally no broad destructive cleanup command.

## Live acceptance checklist

1. Open a learning terminal as the child with `learn-with-dad`. Click the right-side question-mark icon: the Ask Dad popup opens near the top-right. The question is a placeholder; typing needs no deletion.
2. Enter a message, optionally capture a harmless region or paste a PNG, and submit. Dad’s persistent panel must show the same message/image. A request grants no control or privileges.
3. Choose **Watch only**; typing must have no effect. Detach with Ctrl+B, D.
4. Make a fresh request; choose **Help together**. Before child consent Dad cannot type. Child chooses Allow or runs `allow-dad`; Dad types a harmless visible line. Child runs `stop-dad`: Dad disconnects and the learning session remains. Grants expire within five minutes.
5. Choose **Admin demonstration**. Authenticate in Dad’s private terminal. The child’s matching read-only viewer opens automatically, shows harmless admin output, rejects typing and closes when Dad exits/detaches. Never put passwords or secrets in the visible demonstration.
6. Request a repository package through the Omarchy menu. Deny once; the child must see `denied`. Make a **new** request, review and approve deliberately, confirm the package transaction and verify `completed`. Never approve a real install solely for a test without wanting that software.
7. Exercise a named Gaming entry similarly. Unknown/changed/version-mismatched helpers must request manual review, not silently execute unreviewed code. Recheck groups and SSH restrictions after any approved action that explicitly changes privileges (for example controller input access).
8. Check the update request separately when an actual update is wanted; approve privately and finish before arranging any reboot. Recheck assistance after reboot. New or changed migrations require source review.

Do not install the experimental parental policy/PAM/Dino modules as part of this checklist; they have separate deployment gates.
