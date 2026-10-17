# Child-local parental controls (experimental implementation)

**Do not use the previous printable setup guide as a deployment-ready guide for these new controls.** This module is new code, not proof of a tested family installation. No service, account, PAM rule, browser policy or family configuration has been installed on the development PC. Stage in monitoring mode and complete the acceptance gates below before enforcing on a child account. Adults can use assistance without enrolling in parental controls.

## What this build implements

| Module | Implemented behavior | Limits |
| --- | --- | --- |
| Parent policy authority | Root-owned child-local policy, revision checks, last-policy undo, independent parent identities | Parent accounts/keys must be enrolled locally; same-account processes are trusted |
| Screen-time monitoring | Per-day allowances and allowed hours in a named timezone; persistent sampled totals | Counts any logged-in user session while awake, including idle/locked time; not attention or foreground time |
| Time enforcement | Deny new managed logins when blocked; terminate that user's sessions after a configurable grace period | Requires verified PAM/loginctl integration; unsaved work/jobs can be lost |
| Exceptions | Add 15/30 minutes; time pause; temporary browser domain exceptions | Extra minutes do not override bedtime; pause affects time only |
| Browser rules | Optional Chromium domain block/allow rules, Google SafeSearch | Machine-wide, all Chromium users/profiles; other browsers/apps/VPNs are not filtered |
| Parent operations | Terminal menu, private policy snapshots, conflict rejection, changes/request history, daily Markdown totals | No web server; no themed graphical policy forms yet |
| Learner visibility | Locally readable status and a visible desktop warning watcher | Watcher is separate from root enforcement; stopping warnings does not stop enforcement |
| Detailed reports | Existing explicit-import reporting remains available | No automatic foreground-app or browser-visit collector yet |

DNS category filtering, Firefox/other-browser backends, application restrictions, browser activity collection, Notebook import and graphical policy forms are **not implemented**. Do not describe the first browser adapter as comprehensive internet filtering. Every new subject starts with time mode off and browser rules disabled.

## Authority and files

The child PC is the authority; parents can be offline without changing saved rules. Parents each keep a private snapshot and submit an operation through an independently enrolled SSH key. The service checks the Unix socket's kernel-provided UID, not a parent name in a JSON request. Separate dedicated `fl-dad`/`fl-mom` Linux accounts on the child PC give separate identities. Neither is the learner, administrator, viewing, control, notification or relay account.

- `/etc/family-lab/enrollment.json`: administrator-controlled subject UID mappings, parent UID mappings, and approved machine-wide browser backend. No credentials. Readable for PAM, writable only by root.
- `/var/lib/family-lab/policy.json`: current revision and one previous policy, root-only; atomic replacement and fsync.
- `/var/lib/family-lab/usage.json`: root-only counters and timed exceptions. Last 30 recorded daily totals are retained; grants/expired site exceptions are pruned.
- `/var/lib/family-lab/audit.jsonl` and `.previous.jsonl`: root-only parent operation requests/service terminations. Rotation bounds each file to about 1 MiB. An operation request record is not by itself proof that a later disk write succeeded; fetch the actual revision/status after errors.
- `/run/family-lab/policy.sock`: root/`family-lab-parents` only (0660), plus per-request UID authorization. Unknown users cannot use group membership alone to become parents.
- `/run/family-lab/status.json`: local-readable time/status summary, no site history or secrets. May include all enrolled subjects on this machine. Parents should use authenticated get for remote status.
- `/etc/family-lab/gate.json`: minimal persistent enforcement enrollment; active verdicts require a fresh status from the same boot. Never edit it as an ordinary learner.

A parent cannot remotely enroll another system UID or submit commands, filesystem paths, URLs, shell code or browser policy keys. Allowed operations are get, summary, history, apply, undo, extra, pause and allow-site. Policies must match locally enrolled IDs and a strict schema. A submitted policy is limited to 32 KiB. Root administrators remain fully trusted and can recover locally.

## Time semantics and failure behavior

Policy days use an explicit IANA timezone (default UTC); set the household timezone before monitoring. Hours are sorted nonoverlapping windows for each weekday. Split overnight windows across two days. Empty windows mean no permitted hours. Daily limits are 0-1440 minutes per day. Multiple sessions count once per UID. `loginctl` manager sessions are excluded; graphical, TTY and SSH user sessions count. Timing is sampled about every five seconds; it is not exact billing. Attribution around logins/midnight may differ by a sample. Ordinary idle and lock time count; suspend does not advance the monotonic accounting clock. Previously committed totals survive service restart; an interrupted sample can be lost. Long monitor stalls charge at most ten seconds per tick rather than charging an unknown interval.

Daily counters keep the highest recorded date when the wall clock moves backward. This is not a trusted external clock: root, polkit time-changing grants, or compromised system time can defeat wall-clock schedules. Audit those privileges. Pause/site-expiry deadlines use wall time plus Linux boot time within the same boot; suspend cannot extend them. After reboot wall time determines remaining exception lifetime. Root clock changes remain a trust boundary.

Enforcement marks new managed logins blocked immediately after a healthy poll. Existing sessions receive a configured 60-600 second grace period (default 180 for new policies; existing configured values are preserved), persisted across service restart. After it expires `loginctl terminate-user UID` ends **all** that learner's sessions/jobs, including shared terminals. No per-app work preservation is promised. A later login is still denied until hours/allowance permit it or an authorized parent changes the policy.

The login gate attaches to the reviewed Arch `/etc/pam.d/system-login` account stack. Verify that every deployed graphical/autologin/TTY/SSH path includes it and has no earlier PAM sufficient bypass. A custom service bypassing PAM is outside this gate. The root service and PAM helper must be installed on a PC with a standard child account, not one retaining sudo/Docker/empower or other elevation paths.

For an enforced subject, missing/stale verdicts or a rebooted status fail closed for **new logins**. Off/monitor subjects are not denied. Wheel/root administrators remain exempt for local recovery, so never give the child wheel membership. Bus/service failures may leave existing sessions running; denial of new logins is not a substitute for healthy monitoring. Check the actual service status. No public network listener is added.

## Deliberate installation (child PC only)

Read the installer, policy executable and systemd unit first. Keep a verified local parent administrator session open and a recovery USB ready. Audit effective sudo, polkit, Docker and clock privileges first. The installer rejects known administrative/raw-device groups including wheel, docker, empower, disk, input, lxd, incus-admin and libvirt; this is not a complete privilege audit. This workflow is for an existing standard learner user; it does not create/demote the learner or reconfigure the desktop.

Use the local parent admin to create two dedicated parent transport accounts if both parents will manage policy. Names below are synthetic examples, not required names:

```sh
sudo useradd --system --create-home --shell /bin/sh fl-dad
sudo useradd --system --create-home --shell /bin/sh fl-mom
```

Do not give them wheel/sudo. Keep passwords unavailable and verify the local OpenSSH/PAM configuration permits their restricted public-key logins; do not disable PAM or globally enable passwords to bypass an account-lock issue. Expired or disallowed accounts cannot work simply because a key exists. Each account must be used only for its fixed forced-command transport, not as a normal personal login. Root-owned, non-writable authorization files configured through an audited sshd policy are preferable where supported; at minimum ensure no unrestricted duplicate key and no additional credentials for these identities.

Replace CHILD_LOGIN and CHILD_ID with local values. Dry-run first (no --apply):

```sh
python3 scripts/install-parental-controls --subject CHILD_LOGIN --peer CHILD_ID --browser chromium --enable-pam
```

The optional `--browser chromium` approves machine-wide writes to the dedicated `/etc/chromium/policies/managed/family-lab.json`. Omitting it prevents parents from remotely enabling browser rules. Other policy files are not overwritten. Do not use this on Mom's adult PC merely to let her manage the child.

After review, from the local admin terminal:

```sh
sudo /usr/bin/python3 -I scripts/install-parental-controls --apply --subject CHILD_LOGIN --peer CHILD_ID --browser chromium --enable-pam
sudo /usr/bin/python3 -I scripts/install-parental-controls --apply --parent-account fl-dad --parent-label Dad
sudo /usr/bin/python3 -I scripts/install-parental-controls --apply --parent-account fl-mom --parent-label Mom
```

The installer adds the root-owned executable/unit, private state, a parent socket group, and the requested UID enrollments. It backs up the PAM file once before prepending its gate; unknown basic layouts/symlinks are rejected, but that is **not** a full PAM path audit. `pam-ready` means installed, not acceptance-tested. It refuses to add a new subject to an existing policy automatically. It does not start the service, install keys, open firewalls, change sshd or copy private data. Existing policy and usage are preserved. On updates stop the service first, review diffs/backups and rerun deliberately; enrollment/backend changes may require a service restart.

```sh
sudo systemctl enable --now family-lab-policy.service
sudo systemctl status family-lab-policy.service
```

Start with off/monitor modes. Do not enforce while the child is doing unsaved work. This root service needs no desktop autostart; the user warning watcher below does.

## Independent SSH enrollment and parent CLI

Each parent creates a separate passphrase-protected policy key on their own PC. Verify the child's host fingerprint at its console. Enroll Dad's public key only for `fl-dad`, Mom's only for `fl-mom`. Use source restrictions and this single-line prefix before each actual public key:

```text
from="PARENT_SOURCE_IP",restrict,command="/usr/local/libexec/family-lab-policy remote"
```

No PTY, forwarding, user rc, shell, SFTP or administrator rights. The server account's UID determines which parent is recorded. A payload cannot claim to be the other parent. Deleting the parent's UID entry from enrollment rejects new requests immediately (existing group membership alone is insufficient); revoke its key too. Never recycle a revoked UID into another user's account without clearing enrollment.

Parent's SSH config (real values kept outside Git):

```sshconfig
Host family-child-policy
    HostName CHILD_ADDRESS
    User fl-dad
    IdentityFile /ABSOLUTE/PATH/TO/POLICY_PRIVATE_KEY
    IdentitiesOnly yes
    ForwardAgent no
    ForwardX11 no
    ClearAllForwardings yes
    StrictHostKeyChecking yes
    ControlMaster no
    ControlPath none
```

Mom uses her own `fl-mom` account/key and local alias. Add to each parent's existing private Family Lab config:

```json
"policy_aliases": {"alex": "family-child-policy"}
```

`alex` is a synthetic configurable learner ID and must match the child's local policy enrollment. Install `scripts/family-lab-parent` into that parent's `~/.local/bin/` with mode 700 after source review. Load the intended policy key into the existing desktop SSH agent. Then:

```sh
family-lab-parent timezone alex America/New_York
family-lab-parent menu alex
```

Choose daily weekday/weekend allowances, allowed hours, mode, more time, temporary time pause, browser rules, site exception, undo or a Markdown time report. Advanced per-day windows are editable in a private JSON draft: `family-lab-parent get alex` saves its path, and `family-lab-parent apply alex /absolute/path/to/draft.json` uses its revision. Mom and Dad can edit copies independently; a stale revision is rejected with a fetch/review message. No last-writer-wins sync, parent web frontend, shared private key, or both-parents-online requirement.

## Learner status and warning visibility

In the learner's own graphical terminal:

```sh
/usr/local/libexec/family-lab-policy status
/usr/local/libexec/family-lab-policy watch
```

The visible watcher uses existing Omarchy notifications at remaining-time/grace thresholds. Run it with the normal graphical D-Bus environment. It does not approve anything and cannot stop the root service. Stop with Ctrl+C; warning delivery stops but enforcement continues. Test actual desktop delivery before enforcement. No desktop autostart is installed by this prototype. A blocked login screen does not currently have an Ask for more time button; a parent can grant time from their own PC without the child logging in.

## Browser adapter and temporary exceptions

The initial adapter manages **Chromium only**, across the whole enrolled machine. It writes a dedicated managed-policy file with URLBlocklist, URLAllowlist, Google SafeSearch while enabled. User profiles, other applications, DNS category services, VPN/proxy traffic and portable browsers are not sandboxed. This is a supported-browser policy module, not a network firewall or comprehensive content classifier. Google SafeSearch does not filter every search provider. A disabled module writes an empty owned policy file, leaving other administrator policy files alone.

Verify `chrome://policy` shows the intended policies with no errors, no higher-priority conflicts and correct scope. Reload policies/restart Chromium, then test parent-selected allowed/blocked domains, subdomains, private windows and temporary exception expiry. Confirm existing other policy files remain effective. Managed refresh is not instantaneous; do not claim a strict access deadline until observed. A policy-writing error is exposed in parent/status output; the existing browser file may remain active until repaired. Do not delete all policy files to fix it.

Official references: [Chromium/Chrome allow/block administration](https://support.google.com/chrome/a/answer/7532419), [policy allowlist precedence](https://chromeenterprise.google/intl/en_uk/policies/url-allowlist/). Firefox policies and DNS filters remain separate backend work.

## Reports and LocalSend

`family-lab-parent report alex` retrieves authenticated root-owned daily logged-in totals and saves private Markdown under the parent's `~/.local/state/family-lab/policies/`. The menu offers the same export. No activity inference is made from DNS. These reports contain no app/site history because those collectors are not implemented. Share the saved file explicitly through LocalSend's GUI; `family-lab-report share` remains limited to reports in its own original reporting directory. Do not enable unrestricted auto-accept. Notebook import, a unified report/share menu and a safe themed report viewer remain future presentation work.

## Local recovery and removal

From the **local parent administrator**, never a remote policy-only account:

```sh
sudo /usr/local/libexec/family-lab-policy recover
```

Recovery stops the service, preserves the last policy, switches time/browser modules off, clears the persistent enforcement gate, and leaves a readable policy for diagnosis. Invalid usage is preserved under a recovery filename rather than repeatedly crashing restart. It does not delete account keys, undo earlier commands, remove unrelated browser policies, or restart itself. Browser refresh/restart may be needed. Inspect the result before deliberately starting the service again. Root-owned policy/enrollment corruption can still require manual recovery; keep the parent account/USB path.

For removal, recover first, then disable the service. Compare the saved `/etc/family-lab/system-login.before-family-lab` with the **current** PAM file and remove only the added Family Lab header/account line; do not restore an old backup over later package/admin changes. Remove `pam-ready` only after removing the hook. Never delete the executable while a PAM rule still invokes it. Revoke dedicated policy keys/UID mappings, remove only the owned browser file if desired, and retain/delete private data deliberately. A system snapshot is not a backup of all private household files.

## Acceptance gate before family rollout

Run `python3 tests/check_parental.py`: schema/authentication, real socket UID, conflict/undo, persistence, sampled suspend accounting, grace/restart, grants vs bedtime, expiry, retention, recovery exemption, fixed browser/SSH commands. These tests **never install PAM, change live browser policy, or log anyone out**. Run `python3 tests/check_parental_installer.py` as an unprivileged user to stage actual installer file writes under a temporary tree while mocking account/service actions. This checks disabled defaults, permissions, fixed account/service operations and PAM backup creation without touching the live system. Existing assistance tests must also pass.

Then use a disposable Omarchy VM/account and recovery console to verify actual service sandbox permissions, caller-account key enrollment, PAM inclusion for SDDM/autologin/TTY/SSH, denial while blocked, absence of admin lockout, actual `terminate-user` and job termination after warnings, clock/suspend/reboot behavior, offline parents, policy corruption and local recovery. Use short test limits with no unsaved work. Validate Chromium policy recognition and exception expiry in the installed version. Root policy files must be unmodifiable by the child, and all escalation paths audited.

Only after those deployment gates pass should the family installation guide be revised to call this ready for routine enforcement. Installing everything once cannot eliminate future security updates and compatibility tests; the goal is to install a stable module boundary once and make everyday changes through the policy menu.

## Dino experience under development

See [DINO_FLOW.md](DINO_FLOW.md). The design preview and next-session forecast are implemented; the protected login/resume guard, learner action channel and actual hibernation end action are not. Existing enforcement still terminates sessions. Do not deploy it expecting the proposed work-preserving Dino experience.
