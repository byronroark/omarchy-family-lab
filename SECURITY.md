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

The prototype does not provide content filtering, screen-time controls, browser visibility, parent approval authentication, application sandboxing or comprehensive parental controls. Notification cooldowns are not SSH denial-of-service protection. Removing a key prevents new sessions but does not terminate existing ones.

## Public repository hygiene

Only synthetic examples belong in Git. Keep runtime state, SSH directories, credentials, inventories, local configuration, private notes, dumps and captures outside this checkout. Ignore patterns are a convenience, not a secret scanner. Review every staged diff before committing, including tests and screenshots. If a real credential is published, revoke it immediately; deleting the file alone is insufficient.
