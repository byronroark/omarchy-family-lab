# Security policy and boundaries

This is an experimental prototype with no supported production release. Use only in a trusted, agreed local assistance workflow. No security audit or complete multi-PC acceptance test has been performed.

## Reporting a vulnerability

Do not open a public issue containing credentials, exploitable personal configurations or details of a potentially sensitive vulnerability. Use this repository’s GitHub **Security → Report a vulnerability** feature if available. If it is unavailable, open only a minimal issue asking for a private reporting channel; do not disclose vulnerability details there. Maintainers must enable private vulnerability reporting before advertising it as available.

## Required boundaries

- Separate per-helper notification, viewing, optional control, optional scoped relay and administrator keys. Never reuse an admin credential for this workflow.
- Restricted forced commands, source address restrictions, no SSH port/agent/X11 forwarding and verified SSH host keys. Never disable strict host-key checking to get past an error.
- Optional control requires a separately enrolled forced-command key and local interactive confirmation for each pending connection. The initial connection is read-only; approved control lasts at most five minutes and has a visible red status plus a learner revoke shortcut. See [control threat model](docs/CONTROL.md#trust-model-and-limits). Approval grants the learning account’s shell capabilities; revocation cannot undo commands or prevent a malicious approved helper from establishing other access. This is trusted cooperative assistance, not a hostile-controller sandbox. Local confirmation is not human identity authentication.
- Learner starts sharing deliberately. Helper can connect while that dedicated server exists; read-only views need no per-attachment prompt, while each control connection requires fresh approval. Detach/close is not revoke. Stop kills the server and its jobs.
- No secrets, private content, passwords, sudo shells or API keys in a shared terminal. Read-only clients still receive screen output and scrollback.
- Adult learners keep authority over their own PC and can remove the helper’s key or decline assistance. Do not use the tool for covert monitoring.
- Request forwarding is disabled until both helpers enroll a dedicated source/learner-scoped relay key and mappings. Destination attests the source key as **via dad**; it does not authenticate a new direct learner signature. Original IDs/expiry are preserved, retries deduplicate, and a relayed request cannot be forwarded again. Forwarding grants no control, command approval or administrator rights. Requests are retained privately for click actions until their ten-minute expiry and pruned on command activity; they are not an encrypted archive.
- Remote administration requires a separate explicitly authorized account/key and normal interactive privilege checks. `ask-dad`, `ask-mom` and forwarding grant no admin access.
- Standard child accounts must not have unintended sudo, polkit, wheel or Docker daemon access. This policy requires local audit and is not implemented by the tool.
- The optional shell plugin is unsandboxed code inside Omarchy’s shared shell process. Review it before enabling. It invokes only a fixed local CLI/action vocabulary and does not receive keys or grant control/admin approval. Request text is plain text; peer data never supplies a command vector. UI-state JSON alone is not a health certificate: the frontend renews a private heartbeat only after valid state and popup readiness (or when no popup is needed). DND hides inline contents, unknown DND does not certify readiness, and the visible watcher recovers pending requests through the native backend when health expires. A health heartbeat is not proof of human attention. See INLINE_UI.md for limitations.
- The helper desktop account trusts its local code, queue and config. Other local processes under that same account are not isolated from these files.
- No router forwarding, public SSH exposure or Docker socket sharing. Check IPv6 and the active firewall rather than assuming IPv4 rules cover everything.

The assistance prototype does not itself provide parental enforcement or browser visibility. The separate optional policy module adds experimental time enforcement and scoped Chromium rules only after explicit system enrollment; it is not a comprehensive content filter or application sandbox. Notification cooldowns are not SSH denial-of-service protection. Removing a key prevents new sessions but does not terminate existing ones.

## Public repository hygiene

Only synthetic examples belong in Git. Keep runtime state, SSH directories, credentials, inventories, local configuration, private notes, dumps and captures outside this checkout. Ignore patterns are a convenience, not a secret scanner. Review every staged diff before committing, including tests and screenshots. If a real credential is published, revoke it immediately; deleting the file alone is insufficient.

## Optional reporting boundary

The reporting executable is disabled by default on learners. Imported observations are user-owned and not tamper-resistant. Report retrieval requires separately enrolled report-only forced-command keys; assistance credentials do not grant it. Reports are private files, not an encrypted archive; retention cleanup and access audit are not implemented. LocalSend is an explicit interactive export, not parent authentication. Remote Markdown must be viewed with active content and external resource loading disabled. See [reporting limitations](docs/REPORTING.md).

## Optional privileged policy module

Review [the policy trust model and deployment gates](docs/PARENTAL_CONTROLS.md) before installation. The service is root-owned, uses a parent-only Unix socket plus SO_PEERCRED UID authorization, accepts a fixed bounded schema, and cannot receive commands or remote subject enrollment. Dedicated parent transport accounts/keys are distinct from help/admin accounts. Parent account processes and root are trusted. The standard child must lack every elevation path; UID reuse, wheel recovery exemptions, custom PAM bypasses and mutable system time require local audit.

PAM and session termination can deny login or discard work. Keep a verified parent recovery console and USB; never remove a helper executable while its PAM hook remains. Missing/stale health blocks new enforced-child logins; it does not guarantee existing jobs were terminated after a service failure. Chromium policies are machine-wide and bypassable through unsupported applications; inspect policy recognition, scope/conflicts and refresh on the actual release. Root-owned sampled time totals are not evidence of attention, app use or website visits. No live enforcement installation or complete security audit has been performed.

## Polling assistance and parent-approved software

The opt-in master enrollment installs the separate polling runtime under `assistance/`; see [enrollment](docs/ENROLLMENT.md). Ordinary help requests and learner consent never authorize root operations. A parent authenticates through a separate existing administrator SSH identity, reviews a fixed operation from a private parent-owned snapshot and confirms the transaction. Private root receipts prevent replay; only bounded result status is public to the learner. Source hashes and fixed menu IDs replace execution of untrusted menu strings. Child configuration runs without new privileges and with a clean environment.

The admin teaching viewer has a locked system UID and a forced loopback command; its root-owned tmux server enforces read-only access independently of client flags. The learner-owned learning server is different: its owner can change its configuration, so same-account assistance is a trusted workflow, not isolation from a hostile local account. Enrollment checks standard groups and sudo grants but is not a complete polkit, container, device or physical-access audit. The master script does not deploy the experimental policy/PAM modules. A clean-machine enrollment acceptance remains required.

## Delegated approval-only parents

[Approval-only enrollment](docs/APPROVAL_ONLY.md) grants app-install decisions through per-parent locked transport accounts and independent restricted keys; it does not grant parent/child sudo or copy administrator credentials. The root Unix-socket worker authenticates actual peer UIDs against root-owned policy, freezes reviewed package versions, checks expiry/digests and reauthorizes before execution. Decisions share the existing root lock/one-shot receipts. Apps outside explicit delegated scope, updates, agents and input/driver changes require technical help. The parent desktop and its processes are trusted holders of the scoped key; the GUI click is not a separate cryptographic factor.

Technical bootstrap must use independently trusted installer source. Treat the new parent’s enrollment JSON as untrusted data to review; never sudo executable bundle files supplied by a limited approver. Live SSH/systemd/package/GUI acceptance has not yet been performed for this new role.
