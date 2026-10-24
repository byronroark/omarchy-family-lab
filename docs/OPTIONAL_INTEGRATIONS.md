# Optional ActivityWatch reports and AdGuard Home

Both features default off. This first implementation stages reporting adapters,
feature selections and a deployment file. It does not install upstream packages,
start watchers/containers, change client/router DNS, or grant learner Docker access.
No family machine was configured while developing it.

## ActivityWatch reporting

Install upstream ActivityWatch, its browser extension, and reviewed Hyprland/Wayland
window and idle watchers. The classic default X11 watcher is insufficient on
Hyprland. Verify the learner's local dashboard shows the selected buckets with
`web.tab.current`, `afkstatus` and `currentwindow` types. Start with one browser and
profile; matching an app identifier cannot distinguish two profiles of the same app.

**Raw-data disclosure:** ActivityWatch may retain full URLs, page and window titles
in its own local database. Family Lab reads selected events transiently and exports
only app identifiers, domain names and estimated durations. That does not minimize
or erase upstream raw records. Explain collection to the learner, verify private-mode
behavior, and decide retention/deletion before enabling it. Automatic deletion of
ActivityWatch records and Family Lab reports is not implemented in this release.
Keep ActivityWatch bound to loopback. This adapter supports its classic local API,
not authenticated server profiles; never expose the default unauthenticated API to LAN.

As the learner desktop user, use actual bucket/app identifiers, not these placeholders:

```sh
bash master-installation.sh features configure \
  --activitywatch on \
  --web-bucket WEB_BUCKET --window-bucket WINDOW_BUCKET --afk-bucket AFK_BUCKET \
  --browser-app EXACT_BROWSER_APP_ID \
  --acknowledge-raw-activitywatch-storage
```

This prints a plan. Repeat with `--apply` to install the separate report executable
and adapter in `~/.local/bin`, and merge reporting choices into private
`~/.config/family-lab/config.json`. Existing assistance settings/helper enrollment
are preserved. Different installed report executables require a deliberate reviewed
update. It does not start ActivityWatch or any watcher. `--activitywatch off --apply`
disables this adapter, but does not erase records or downloaded reports.

```sh
family-lab-report generate 2026-10-24 2026-10-24
```

Remote reports still require separate report-only SSH keys, fixed forced commands
and `allowed_helpers`, as described in REPORTING.md. Never reuse a policy/admin key.
Parents can install the executable with feature setup in off mode, then configure
private `reporting.report_aliases` explicitly. No SSH access is automatically enrolled.

The new Family Manager **Website and app report - today (UTC)** action uses that
separate report route. **Save private time report** remains the root-owned logged-in
time report. They measure different things and must not be added together. Dates
currently mean UTC, not household local midnight. LocalSend sharing stays explicit.

### Time allocation and limits

- Intersect non-idle and active-window intervals. Attribute domains only where the
  selected non-private browser-tab stream overlaps a configured foreground browser.
  Browser time is already included in application time.
- Strip URL paths, queries, credentials and titles from exports. Missing private-mode
  metadata and internal URLs receive no domain attribution.
- Gaps remain unknown; these are estimates, not proof of attention or learning.
  No automatic cloud/AI upload occurs. Learner-owned source data is editable.
- Loopback-only GET calls bypass proxies and reject redirects. Bytes/events are
  bounded; unsupported schemas and ambiguous overlaps fail instead of inventing totals.
- A bounded one-day lookback handles ordinary cross-midnight events. Longer merged
  events starting earlier can be omitted and remain unknown. The 10,000-event limit
  can require a shorter report range.

## AdGuard Home

Prefer an always-on administrator-managed host; a hibernating learner PC or sleeping
parent desktop is a poor household DNS dependency. Never grant the learner Docker
access. Register an existing verified HTTPS management URL on the parent's account:

```sh
bash master-installation.sh features configure \
  --adguard existing --adguard-url https://YOUR_VERIFIED_FILTER_HOST
```

Review, then repeat with `--apply`. **Open content filter** opens upstream management
in the browser; no password is stored in Family Lab. Registration does not prove the
child uses this DNS or that filtering is healthy. A trusted HTTPS endpoint is an
explicit deployment prerequisite; TLS checks are never disabled. Specify all desired
features together: omitted selections default off, including an existing AW adapter.

For a new deployment, obtain/review an official stable image digest and run:

```sh
bash master-installation.sh features adguard-compose \
  --image adguard/adguardhome@sha256:REVIEWED_64_HEX_DIGEST \
  --dns-bind DEDICATED_HOST_LAN_IPV4 \
  --output /ABSOLUTE/PRIVATE/PATH/adguard.compose.json
```

Plan only by default; `--apply` writes a private Compose file outside Git. It never
starts Docker. Management is loopback-only, DNS binds to the selected private IPv4,
and no DHCP/encrypted-DNS ports or privileged/host-network container are configured.

Administrator acceptance steps:

1. Reserve the host address and check port 53 TCP/UDP and loopback ports 3000/8080,
   existing resolver services and firewall rules. Never disable the current resolver
   or rewrite `/etc/resolv.conf` automatically to resolve a collision.
2. Review/start the generated file using the host's Docker Compose installation.
   Work/config volumes persist beside the file. Use the host console or authenticated
   SSH tunnel for initial setup on loopback port 3000.
3. Complete the upstream wizard. For later management use container port 80 (mapped
   to host loopback 8080). Configure credentials, DNS access restrictions, upstreams,
   per-client rules and retention. Parent-accessible HTTPS management is separate work.
4. Record original DNS settings, test one chosen client first, including IPv6 and
   browser encrypted DNS, and verify client identity. Then test blocks, exceptions,
   server restart and restoration of the original DNS configuration.
5. Only afterward consider household router/DHCP changes. An unfiltered secondary
   resolver is not guaranteed to be used only when the filtered resolver fails.

Rollback: restore recorded client/router DNS, verify resolution, then stop/remove
AdGuard if desired. Do not delete its private data volumes without a separate decision.
Upgrades require a reviewed digest and backup.

This phase opens upstream controls; it does not import AdGuard DNS logs, implement
Family Lab filtering forms or apply exceptions via the AdGuard API. Pi-hole is a future
adapter for existing installs. DNS activity is not browsing visits or website minutes.
DNS filtering cannot distinguish pages on the same hostname or guarantee coverage
when a VPN/alternate DNS path is used.

## Verification

`python3 tests/check_optional_features.py` uses synthetic data, a temporary real
loopback HTTP fixture, fake private homes and generated deployment files. Real watcher
behavior/version compatibility, idle/private-mode handling, source retention, report
SSH enrollment, AdGuard port mappings and DNS rollback still need machine acceptance.

Primary references checked October 24, 2026:

- https://docs.activitywatch.net/en/latest/api/rest.html
- https://docs.activitywatch.net/en/latest/watchers.html
- https://docs.activitywatch.net/en/latest/privacy.html
- https://adguard-dns.io/kb/adguard-home/getting-started/
- https://adguard-dns.io/kb/adguard-home/docker/
