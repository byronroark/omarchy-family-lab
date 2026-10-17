# Security policy and boundaries

This is an experimental prototype with no supported production release. Use only in a trusted, agreed local assistance workflow. No security audit or complete multi-PC acceptance test has been performed.

## Reporting a vulnerability

Do not open a public issue containing credentials, exploitable personal configurations or details of a potentially sensitive vulnerability. Use this repository’s GitHub **Security → Report a vulnerability** feature if available. If it is unavailable, open only a minimal issue asking for a private reporting channel; do not disclose vulnerability details there. Maintainers must enable private vulnerability reporting before advertising it as available.

## Required boundaries

- Separate notification, viewing and administrator keys. Never reuse an admin credential for this workflow.
- Restricted forced commands, source address restrictions, no forwarding and verified SSH host keys. Never disable strict host-key checking to get past an error.
- Learner starts sharing deliberately. Helper can connect while that dedicated server exists; no per-attachment consent prompt is implemented. Detach/close is not revoke. Stop kills the server and its jobs.
- No secrets, private content, passwords, sudo shells or API keys in a shared terminal. Read-only clients still receive screen output and scrollback.
- Adult learners keep authority over their own PC and can remove the helper’s key or decline assistance. Do not use the tool for covert monitoring.
- Remote administration requires a separate explicitly authorized account/key and normal interactive privilege checks. `ask-dad` grants no admin access.
- Standard child accounts must not have unintended sudo, polkit, wheel or Docker daemon access. This policy requires local audit and is not implemented by the tool.
- The helper desktop account trusts its local code, queue and config. Other local processes under that same account are not isolated from these files.
- No router forwarding, public SSH exposure or Docker socket sharing. Check IPv6 and the active firewall rather than assuming IPv4 rules cover everything.

The prototype does not provide content filtering, screen-time controls, browser visibility, parent approval authentication, application sandboxing or comprehensive parental controls. Notification cooldowns are not SSH denial-of-service protection. Removing a key prevents new sessions but does not terminate existing ones.

## Public repository hygiene

Only synthetic examples belong in Git. Keep runtime state, SSH directories, credentials, inventories, local configuration, private notes, dumps and captures outside this checkout. Ignore patterns are a convenience, not a secret scanner. Review every staged diff before committing, including tests and screenshots. If a real credential is published, revoke it immediately; deleting the file alone is insufficient.
