# Approval-only parent enrollment

A parent can be the technical helper or an approval-only parent, independently of whether the child calls them Mom, Dad or another name. This release adds approval-only access alongside the existing technical deployment. It does not require giving the new parent the technical administrator’s SSH key, password or shell.

**Status:** isolated protocol, persistent-job, UI and enrollment tests pass. The existing technical parent’s endpoint-only upgrade is live: SSH restrictions, socket policy, old technical access, and password-free deny/approve cards passed with a real child-menu request. The approved package was already installed, so no new package was added. Clean enrollment on a second parent’s PC and installation of a newly absent package still need live acceptance. This is not a whole-machine security audit.

## What the parent sees

The existing style of persistent request card shows the child’s message and a root-reviewed app plan. The parent can choose **Approve installation**, **Deny request**, or **Dismiss**. A scrollable list includes exact repository/package versions and resolved dependencies. The parent gets queued/running/completed/failed status in the same window, and the child’s existing request view receives the result. Closing the parent window does not cancel an accepted job.

Unsupported actions show **Technical helper needed** with Deny/Dismiss; they have no approve button and cannot be approved by calling the backend directly. Ordinary learning/admin help also offers no technical-session buttons on this account. The technical helper continues receiving the original requests independently and receive the same quick approval path on new enrollment while retaining private administrator review.

This first release delegates reviewed **app installation** only:

- Named app menu entries in the technical administrator’s allowed scope, limited to the reviewed `package` and `script` modes. Source changes require technical review.
- Optional exact repository/package names explicitly added to the scope by the technical administrator.
- No arbitrary commands, shell flags, local package files, AUR builds, full Omarchy updates/migrations, default agents, controller/input-group changes, root demonstrations or shared-terminal typing.

New enrollment defaults to the reviewed app menu set; the administrator must inspect and can narrow that scope before installation. Repository package requests outside the explicit allowlist need the technical helper. The updater remains on the existing private administrator path until a separately reviewed noninteractive updater is implemented. This is not automatic approval of every sudo prompt.

## Quick approvals for technical Mom or Dad

New technical and approval-only parents receive the same **Approve installation / Deny request** card without administrator authentication for each scoped app request. Technical parents additionally get **Review in admin terminal** for hands-on review. Their ordinary help requests keep Watch only, Help together and Admin demonstration; approval-only parents do not receive those tools. Unsupported actions, updates and default agents need the private administrator path; quick approval never expands its scope automatically. If the worker cannot prepare a review, the technical card explicitly offers admin review instead of silently approving or changing credentials.

Every new enrollment includes scoped approve/deny access automatically and requests a stable parent ID and the reviewed app scope. The technical/approver choice controls additional help and admin tools, not access to the approval cards. The technical role still requires the encrypted administrator identity. An independent fourth role key is generated for the restricted approval transport; the existing poll/view/control keys and separate admin alias remain. Existing profiles without `helper.quick_approval` keep their original behavior.

To add this to an existing **master-script-managed** technical enrollment, retain its private profile, learner ID, administrator identity, helper role and existing keys. Set `helper.quick_approval` to `true`, add a stable `helper.id`, and review an `approval_scope` containing `packages` and `menus` (the same format as approval-only enrollment). Run helper `plan`, `apply` and `bundle` to generate the additional key and updated card. Copy only the exported enrollment JSON to a private administrator-owned location on the child. From independently trusted installer source, add just the endpoint:

```sh
sudo ./master-installation.sh apply --role learner --approval-transport-only --profile "$HOME/.local/state/family-help/technical-approval-enrollment.json"
sudo ./master-installation.sh verify --role learner --profile "$HOME/.local/state/family-help/technical-approval-enrollment.json"
```

This endpoint-only mode preserves learner help keys, menus, viewer and desktop files. Fresh technical learner enrollment installs both phases automatically. The full learner and approval endpoint phases have separate transactions: if the second phase fails, the first may already be installed. Preserve recovery access and rerun deliberately. An older manually deployed household setup needs configuration/key reconciliation first; do not overwrite its profile or regenerate its existing keys blindly. Neither changing `helper.quick_approval` to `false` nor deleting a local alias revokes the remote key: follow the registry/key revocation steps below.

When multiple parents see the same request, only the first accepted decision can run. This applies across quick approval and the existing administrator review path. Quick and administrator review share the action lock and one-shot receipts.

## Trust and execution boundary

Each approval-only parent has an independent unattended Ed25519 key on their own desktop. It grants only their configured app approval scope. Treat the desktop account and all processes under it as trusted: a mouse click is the application’s consent UI, not an independent cryptographic factor. Protect the private key, lock the parent desktop and do not share that login with the child. No administrator key is copied there.

On the child PC, a separate locked system transport account (`familyap-<parent-id>`) has a root-owned SSH key file and forced bridge command. Effective SSH settings require public-key authentication, disable TTY/forwarding/user startup hooks and prohibit password authentication. Its home is root-owned. It has no sudo grant and is separate from learner, administrator and teaching viewer UIDs. The child never joins the approval transport group.

The bridge accepts one bounded JSON message and connects to a root/group-owned Unix socket. The root worker authenticates the **actual Unix peer UID** and the root-owned parent registry before parsing operations; caller-supplied labels, UIDs or role names cannot grant access. No new TCP listener or SSH server on the parent PC is added.

The worker stores the request snapshot, resolved package versions, short review ticket, digest and expiry privately. The decision must match that parent and review. It recomputes the plan before queueing and before execution; a changed source, package set/version, scope or expired ticket stops it. The package command uses only the pinned transaction with fixed noninteractive flags. Package signatures and hooks remain the distribution package manager’s trust boundary: an app install is a real system change, not a sandbox.

The worker shares the existing root action lock and one-shot receipts with technical approvals. Only the first decision wins. A receipt is durable before a job can execute; an interrupted or partly persisted job is never automatically replayed. Parent connection loss cannot launch a second install. A queued job is reauthorized against current parent permissions; revocation stops new work but does not undo an already running package transaction.

Personal app configuration uses the existing child phase with `setpriv`, `--no-new-privs`, a clean environment, closed parent descriptors and no stdin/admin agent. No child configuration code is elevated. Private request/review/audit/job records stay under `/var/lib/family-software`; the child sees only bounded public status. Retention cleanup is not automated yet.

## Prerequisites

The child already needs the technical assistance deployment with the separate administrator, existing SSH service and reviewed `family_software.py` / `family_menu.py` APIs. Approval enrollment refuses incompatible installed APIs and does not replace the technical helper’s keys, learning session, menus, widget or desktop configuration. The new parent can have a fresh Omarchy install with Python/GI/GTK and the normal desktop helpers.

Keep verified technical administrator SSH and console recovery. Choose stable child/parent IPs and verify the child’s Ed25519 host fingerprint at its physical console. The parent device is a client; its SSH server can remain disabled.

## 1. Prepare the parent profile on the fresh parent PC

From a reviewed checkout, as that parent’s normal desktop user:

```sh
./master-installation.sh configure
./master-installation.sh plan --approval-only
./master-installation.sh apply --approval-only
./master-installation.sh bundle --approval-only --out "$HOME/.local/state/family-help/approval-enrollment"
```

Choose Mom, Dad or another label, then **approver**. Supply a stable approval parent ID (up to 20 plain login characters), the existing child/admin login names, device addresses and verified host fingerprint. The administrator login identifies who will bootstrap the service; **no administrator private-key path is requested or accepted** for this role. Optional extra package allowlist entries must use exact `repository/package` names.

Helper apply generates just the restricted approval key, pins the child host and installs the parent watcher. It does not enroll view/control/admin aliases. A profile cannot silently switch an existing technical desktop to approval-only: old administrator credentials must be audited/revoked deliberately, or use a fresh desktop account.

## 2. Technical administrator reviews and installs the enrollment

Transfer **only `enrollment.json`** from the parent’s bundle to a private location owned by the existing administrator on the child PC. Use an already trusted transfer route; this file contains household details and public keys, not private keys.

**Run installer code from the technical administrator’s independently trusted, verified checkout—not executable files supplied by the approval-only parent.** Otherwise accepting someone’s bundle as root would itself give them administrator-level code execution. The root installer refuses symlink/FIFO/oversized profiles and requires the file and its ancestors to be owned by root/the selected administrator without group/world write access. Keep the copied profile outside `/tmp` and outside the repository. Review the JSON as data, especially the child, parent ID/public key/source IP and delegated package/menu scope. Remove any apps that should require technical review.

In the existing technical administrator’s SSH terminal on the child, using that trusted checkout:

```sh
./master-installation.sh plan --approval-only --profile "$HOME/.local/state/family-help/new-parent-enrollment.json"
sudo ./master-installation.sh apply --role learner --approval-only --profile "$HOME/.local/state/family-help/new-parent-enrollment.json"
sudo ./master-installation.sh verify --role learner --approval-only --profile "$HOME/.local/state/family-help/new-parent-enrollment.json"
```

Enter the technical administrator password privately. `--approval-only` refuses a profile that requests the technical role. This adds the locked transport account, root-owned key/Match rule, registry entry and root Unix-socket worker. Existing technical access and unrelated approver registry entries are preserved. SSH syntax and effective forced-command policy are checked before reload; sudo/group checks reject an unexpectedly privileged child or transport account. No package is installed by enrollment and no sudoers file is added.

The socket is enabled; the service starts on demand. Re-enrollment reloads authorization without intentionally restarting a running package job. Managed-file backups/drift refusal apply. System accounts, directories, service enablement and cross-machine changes are not one atomic transaction: preserve recovery access and inspect errors before retrying.

Back on the parent desktop:

```sh
./master-installation.sh apply --approval-only --activate
./master-installation.sh verify --approval-only
```

Do not run the full technical learner enrollment again to add this parent; that would be the wrong path. The approval branch adds another recipient while retaining the existing technical recipient. Parent watchers currently handle one child per desktop profile, and the child request queue still contains the latest request rather than an unbounded inbox.

## Live acceptance before relying on it

1. Confirm the parent cannot open a shell, allocate a PTY, forward a port, access an admin demonstration or obtain shared-terminal typing using the approval key. Inspect effective SSH policy and the transport account’s groups/sudo listing.
2. On the child, request an allowed, already-installed repository package (explicitly allowlist it for the test) and deny it on the new parent’s card. Child and parent must both see `denied`; no package job runs.
3. Make a new allowed request. Check the exact root-reviewed package/dependency versions, approve once, and verify actual completion. Use software that the family really wants installed for a real transaction.
4. Close the parent view while work is queued/running. Verify the result through the child status view and that reconnecting/repeated clicks do not execute twice.
5. Submit an out-of-scope package, update, agent, controller or changed menu helper. There must be no approval button or backend execution; the technical route remains available.
6. Repeat an old decision, alter a review digest, let a review expire and revoke a parent before a queued job starts. All must fail without new execution. Recheck Dad’s existing watch/consent/admin flow.
7. Re-run enrollment unchanged and inspect the file-change report, then check request delivery after a normal reboot arranged separately.

## Revocation and recovery

Disable the parent’s root registry entry (`enabled: false`) and reload `family-help-approval.service` if active. The worker rechecks the on-disk permissions and Unix identity before new decisions/jobs. Remove the corresponding root-owned public key to prevent new SSH connections. Existing SSH processes and already-running package jobs need deliberate review; revoking a key is not package rollback.

Never remove the shared worker/socket while another parent or a running job uses it. Failed/interrupted jobs require a **fresh request** after the technical helper inspects the system; do not delete receipts to force replay. Preserve private audit records. A technical helper can still use the established private admin workflow if the approval service is unavailable.
