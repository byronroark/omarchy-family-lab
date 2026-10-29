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
or erase upstream raw records. Explain collection to the learner and verify private-mode
behavior before enabling it. The separate
`integrations/family_activitywatch_retention.py` helper previews expired events by
default; `--apply` deletes them. It targets only this hostname's window, idle and
browser buckets on loopback port 5600. Events starting more than 14 days ago are
removed whole, including merged events crossing the cutoff. It also deletes
`report-*.md` files older than 14 days from the executing user's report folder.
Imported snapshots, exported files, other computers' buckets and backups are not
covered. Feature selection does not install or schedule cleanup: install it in the
desktop user's private executable directory, schedule it hourly, and verify an
initial successful run. It never logs event content or creates raw-data backups.
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

## Family Manager controls (requires separate enrollment)

Open **Collection and filtering settings** in Family Manager. The panel keeps its
own status/error feedback without discarding the parent's schedule edits. Unready
backends disable their controls. Refresh fetches actual backend status; it does not
infer an enabled state merely from a saved checkbox.

### Collection control permission

Ordinary report-only enrollment remains read-only. A technical administrator must
explicitly add `--allow-collection-control` when enabling the ActivityWatch reporting
feature on the learner. This grants all enrolled `allowed_helpers` start/stop access
to one fixed user target through their report SSH role; it does not grant a shell,
root, arbitrary unit selection or policy editing. Prefer fresh separately scoped
report keys if the household wants to keep its old read-only report keys unchanged.
Removing the flag during explicit setup removes that permission for future requests.

Before this grant, the administrator must review/install ActivityWatch and the
appropriate Wayland watchers and supervise them under the fixed learner user units:

- `family-activitywatch.target`
- `family-aw-server.service`
- `family-aw-watchers.service`

Templates live in `systemd/activitywatch/`. The `.example` service paths are
placeholders, not installable working commands. Replace them with reviewed upstream
executables on that device. A Wayland watcher such as upstream `awatcher` can provide
window and idle buckets; test both schemas. Review availability and behavior before
choosing it. Install the reviewed units for the learner, reload that user's service
manager and test start/stop manually before allowing remote control. Stop independent
ActivityWatch/autostart instances to prevent duplicate or unsupervised collectors.
No collection target is enabled at login by these templates.

The adapter requires both services to be loaded and `PartOf` the fixed target. It
checks target/service active state after changes. **Active service is not proof of
complete event coverage.** Stop controls the supervised processes only; it does not
erase history or disable a browser extension, which may retain queued events while
the server is down. Turn off the extension as well when a full browser-collection
pause is intended. A separate visible learner control for that extension remains
upstream functionality. No claim is made that the learner cannot tamper with their
own user services or raw records.

The panel requires an explicit raw URL/title storage acknowledgement before Start.
For deliberate CLI use, `family-lab-report control PEER status/start/stop` uses the
same fixed endpoint; the `start` command itself is the explicit acknowledgement.
No automatic retry of a mutating command occurs after a lost reply.

### Per-learner AdGuard control enrollment

A parent must first configure a persistent, device-specific AdGuard client with
explicit per-client settings (`use_global_settings: false`) and verify its exact
identifiers and DNS routing. No CIDR/wildcard/group entry is allowed. Each parent
who needs native controls provides a private, parent-owned, mode-0600 file at
`~/.config/family-lab/adguard-control.json` with these fields:

```json
{
  "url": "https://YOUR_VERIFIED_ADGUARD_ORIGIN",
  "username": "YOUR_ADGUARD_ACCOUNT",
  "password": "YOUR_PRIVATE_PASSWORD",
  "peer": "YOUR_STABLE_LEARNER_ID",
  "client_name": "YOUR_EXACT_PERSISTENT_CLIENT_NAME",
  "client_ids": ["YOUR_EXACT_DEVICE_IP_OR_CLIENT_ID"]
}
```

Never put the completed file in Git, the setup profile, a screenshot or a report.
This is an AdGuard administrator credential, **not a restricted read-only token**;
AdGuard authorization determines its broader power. Family Lab's adapter limits
itself to the enrolled client. Use only on a trusted parent's account. It verifies
HTTPS normally, rejects redirects/proxies and bounds responses; there is no insecure
TLS mode. Password storage in the desktop keyring is future work.

Enable/Disable changes only that client's blocklist, parental-domain and safe-browsing
booleans, preserving its other settings and all other clients. SafeSearch and blocked
services remain separate upstream settings; disabling these three switches is not a
promise that every possible DNS restriction is removed. A client identity change or
inherited settings is rejected. Global AdGuard protection is never toggled; if paused,
restore it through upstream management before enabling this learner's controls.

Settings are read back after a change. A pre-write recheck detects intervening edits,
but AdGuard's client-update endpoint provides no revision/CAS guarantee: avoid
simultaneous edits of the same client in two parents' windows or upstream management.
The panel confirms settings, not traffic coverage; test actual resolution and blocks.

`tests/check_integrations_controls.py` exercises fixed-unit permission boundaries,
service failures, private credentials, identity changes, per-client scope and
unconfirmed writes with mocks only. No collection or filtering was enabled on family
PCs during development. Primary API contract:
https://github.com/AdguardTeam/AdGuardHome/blob/master/openapi/openapi.yaml
