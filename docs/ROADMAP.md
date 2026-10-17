# Roadmap toward an Omarchy shell plugin

This is a community proposal and implementation path, not an acceptance commitment from Omarchy maintainers.

## Milestone 1 — auditable CLI prototype (current)

Generic roles, local-only examples, explicit sharing and revocation, restricted SSH transport, desktop notification action, bounded queue, basic tests, staged deployment and documented limits. Full SSH/desktop acceptance remains pending.

## Milestone 2 — verified multi-PC workflow

Test separate learners and hosts, adult-admin and child-standard roles, fresh installs, SSH negative cases, missing/changed host keys, client/source identity, sleep/logout/reboot, stale requests, daemon failure, click actions and stop behavior. Record a real supported-version matrix using sanitized results. Add automated transport tests with disposable accounts/containers where appropriate. Harden the receiver boundary and review terminal-content risks before a supported release.

## Milestone 3 — extract adapters and package

Separate transport, session control, request schema, configuration validation and Omarchy desktop integration. Specify a versioned local protocol with fixed action names, no arbitrary remote shell instructions. Provide safe upgrades, rollback, migrations and removal. Decide how a neutral alias for ask-dad should work without breaking the original command. Make installation reviewable and preserve local SSH/firewall policy.

## Milestone 4 — actual shell plugin

Verify the current official shell plugin loader, manifest and supported APIs from installed source/upstream documentation. Build an adapter that shows sharing state, participant requests, attachment status, expiry and an explicit stop button. Make helper and learner modes obvious. Integrate login/logout lifecycle without enabling unattended sharing, persistent privilege or user lingering. Add visible error states and fallback operations. Validate hot reload, upgrade/removal and compatibility on declared Omarchy releases.

A plugin must not become a general remote-command executor, collect administrator keys, create passwordless sudo rules, bypass consent, or silently expose ports. A consented remote-control mode, if ever proposed, is separate from this read-only design and requires its own threat model.

## Milestone 5 — upstream discussion and possible distribution

Prepare a narrowly scoped proposal, security model, demonstrated acceptance results, license, documented maintenance commitment and plugin package. Ask maintainers which contribution/distribution path they support. Adopt their current conventions and review process. Only describe the project as official if the maintainers explicitly accept and authorize that status.

Application-specific setup, GPU drivers and unidentified third-party plugins stay outside the core. Optional future guides must use verified sources and must never bundle personal inventories or credentials.
