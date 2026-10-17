# Roadmap toward an Omarchy shell plugin

This is a community proposal and implementation path, not an acceptance commitment from Omarchy maintainers.

## Milestone 1 — auditable CLI prototype (current)

Generic roles, local-only examples, explicit sharing and revocation, restricted SSH transport, desktop notification action, bounded queue, basic tests, staged deployment and documented limits. Optional consented control now adds a separate key, local connection-specific approval, visible status, bounded duration and revocation; its trust model is in CONTROL.md. Multiple helper destinations and one-hop authenticated request forwarding are implemented as an opt-in CLI/notification-menu adapter; ROUTING.md documents its trust boundaries. Full SSH/desktop acceptance remains pending.

## Milestone 2 — verified multi-PC workflow

Test separate learners and hosts, adult-admin and child-standard roles, fresh installs, SSH negative cases, missing/changed host keys, client/source identity, sleep/logout/reboot, stale requests, daemon failure, click actions and stop behavior. Record a real supported-version matrix using sanitized results. Add automated transport tests with disposable accounts/containers where appropriate. Harden the receiver boundary and review terminal-content risks before a supported release.

## Milestone 3 — extract adapters and package

Separate transport, session control, request schema, configuration validation and Omarchy desktop integration. Specify a versioned local protocol with fixed action names, no arbitrary remote shell instructions. Provide safe upgrades, rollback, migrations and removal. Keep `ask-dad` and `ask-mom` as familiar aliases over generic `family-lab ask HELPER MESSAGE` routing. Preserve independent helper keys, explicit one-hop forwarding and unchanged consent. Make installation reviewable and preserve local SSH/firewall policy.

## Milestone 4 — experimental shell plugin (initial adapter implemented)

An initial service manifest, themed inline request card and fixed-action adapter are implemented against inspected Omarchy 4.0.4-1 / Quickshell 0.3.1 APIs; see INLINE_UI.md. Synthetic headless rendering and a real Wayland popup smoke check passed. Next expand deployment coverage and add visible learner sharing state, attachment status and a carefully scoped stop surface. Those broader controls are not yet in the request card. Make helper and learner modes obvious. Integrate login/logout lifecycle without enabling unattended sharing, persistent privilege or user lingering. The experimental plugin now renders **Ask Mom** inline on its own card; the stock notification service is unchanged and the native adapter retains its click-through menu. Show original learner and relay provenance, delivery failure and original expiry. Do not confuse forwarding with parental command approval or a terminal-control grant. Add visible error states and fallback operations. Validate hot reload, upgrade/removal and compatibility on declared Omarchy releases.

A plugin must not become a general remote-command executor, collect administrator keys, create passwordless sudo rules, bypass consent, or silently expose ports. The current consented terminal-control prototype has a separate opt-in key and documented threat model; a future plugin must preserve those boundaries and display its state clearly.

## Milestone 5 — upstream discussion and possible distribution

Prepare a narrowly scoped proposal, security model, demonstrated acceptance results, license, documented maintenance commitment and plugin package. Ask maintainers which contribution/distribution path they support. Adopt their current conventions and review process. Only describe the project as official if the maintainers explicitly accept and authorize that status.

Application-specific setup, GPU drivers and unidentified third-party plugins stay outside the core. Optional future guides must use verified sources and must never bundle personal inventories or credentials.
