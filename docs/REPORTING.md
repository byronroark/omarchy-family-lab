# Optional Markdown reporting — experimental foundation

Reporting is off by default and independent of terminal assistance. This release supports **imported observations**, Markdown generation, separately authorized SSH retrieval, and interactive LocalSend sharing. It does not collect desktop/browser activity, implement the themed report viewer, or enforce parental controls. An empty report means missing coverage, not no computer use.

## Install and enable deliberately

Review `scripts/family-lab-report`, then copy it to `~/.local/bin/family-lab-report` with owner-only executable permissions. Install the same version on the learner and helper PCs. This is a separate executable; the existing `family-lab install` does not install it. No administrator privileges are needed for this foundation. From the reviewed repository directory:

```sh
mkdir -p ~/.local/bin
install -m 700 scripts/family-lab-report ~/.local/bin/family-lab-report
```

This replaces an existing report executable at that path; review any local changes first.

Merge the appropriate `reporting` object into the existing private `~/.config/family-lab/config.json`; preserve all existing settings.

Learner (only after explaining collection to the learner):

```json
"reporting": {"enabled": true, "allowed_helpers": ["dad", "mom"]}
```

Helper:

```json
"reporting": {"report_aliases": {"learner-a": "family-learner-a-report"}}
```

Enroll **new, separate report-only SSH keys**, one per helper. In the learner account's authorized_keys use `restrict`, a reviewed source-address restriction where practical, and a fixed absolute forced command such as `/ABSOLUTE/PATH/family-lab-report serve dad`. Replace the entire placeholder with the installed executable's real absolute path. Mom's key fixes `serve mom`. Never reuse a view, control, notification, relay, or admin key. Configure the helper's SSH alias with the verified host key, report-only IdentityFile, and IdentitiesOnly yes. The endpoint ignores SSH_ORIGINAL_COMMAND and accepts only bounded JSON containing start/end dates. It can disclose all retained observations in a permitted range; it is not a per-report child approval prompt.

Removing a helper from allowed_helpers rejects new requests. Revoking a key does not erase previously downloaded reports. Do not deploy this prototype as a tamper-resistant parental-control service: the learner account owns the imported data/config and can change them.

## Observation contract

Import explicitly with `family-lab-report import /path/to/private-observations.json`. This **replaces** the snapshot, rather than appending or merging it. Only import locally reviewed data; never place household observations in this repository.

```json
{
  "schema": 1,
  "coverage": "Synthetic demonstration, not real activity",
  "observations": [
    {"start": "2026-01-01T10:00:00+00:00", "end": "2026-01-01T10:20:00+00:00", "app": "Browser", "domain": "example.org", "category": "Learning"}
  ]
}
```

Intervals must be timezone-aware, sorted, nonoverlapping, and at most one day each. A browser interval is one foreground interval with an optional domain, not a second interval added to app time. Domains are lowercase ASCII hostnames (internationalized names need ASCII encoding); full URLs and search strings are rejected. App/category labels are short plain text. No page titles, commands, keystrokes, screenshots, or page contents are accepted as separate fields. Labels/coverage remain caller-supplied claims, not independently verified observations. Import validation cannot detect sensitive content hidden inside a label.

## Generate, request, and share

```sh
family-lab-report generate 2026-01-01 2026-01-07
family-lab-report request learner-a 2026-01-01 2026-01-07
family-lab-report share /absolute/path/printed/by/the/previous/command.md
```

Dates are inclusive **UTC** dates, with at most 31 days per report. Cross-midnight intervals are clipped to the requested period. UTC is explicit in reports; a selectable household timezone is future work. The command prints a private local report path under `~/.local/state/family-lab/reporting/`. Reports include totals, app/domain/category tables, text bars, and coverage caveats. Website time is already included in app time. No images or PDF runtime are needed.

LocalSend is an optional delivery adapter. `share` invokes `localsend-cli send FILE` with interactive destination selection and normal receiver acceptance. No broadcast-to-both, auto-accept, automatic retry, or unattended destination trust is enabled. Upstream documents this client, but an installed desktop LocalSend package may not include it: check the installed client's help/version and use the GUI's file picker if unavailable. [Upstream LocalSend CLI documentation](https://github.com/localsend/localsend#command-line-interface). A successful process exit is not proof that a parent read the report. The plugin has no delivery-status UI yet.

SSH retrieves only into a local private file; it never renders returned Markdown or runs embedded commands. Treat any remote report as untrusted text: use a viewer that disables raw HTML, scripts, automatic remote images, and automatic external resource loading. Never automatically open links. LocalSend's recipient alias is not an enrolled parent identity; confirm the recipient before sending sensitive reports.

## Privacy, retention, and support

Files are created owner-only; this is file permissions, not encryption at rest or isolation from other processes under the same account. No report is published, sent to AI, or shared automatically. LocalSend transfers leave the module's access boundary; recipients control their copies.

This foundation has **no scheduled retention cleanup or access audit yet**. The imported snapshot persists until replaced/deleted, and generated/downloaded reports persist until deleted. Parents must remove unneeded private files deliberately. Do not advertise the proposed seven-day/30-day retention as implemented.

- Disabled: enable explicitly on the learner after review.
- No observations: no collector/import is available; missing time stays unknown.
- SSH denied: check the separate report identity, fixed helper enrollment, and verified host key. Never disable host-key verification.
- LocalSend unavailable: open LocalSend and select the saved file manually.
- Offline child: retrieval fails; no fabricated report or automatic resend occurs.

Run `python3 tests/check_reporting.py` for hermetic checks. Real SSH enrollment, installed LocalSend compatibility, and a two-PC acceptance test remain required before household use.

## Optional Uber Notebook presentation (proposed)

Uber Notebook's documented command interface can import Markdown as Pages with headings, tables, callouts, and columns. It is a candidate for a local Family Lab hub, dated report pages, and parent guides. This release does not import into it automatically. LocalSend delivers a file; it does not automatically add that file to a notebook.

A future explicit “Add to Uber Notebook” adapter must use `omarchy-shell uber-notebook` commands, look for an existing parent page before creating one, handle the documented initial file-read retry, and disclose that imported reports create another retained copy (including notebook history/backups). Do not write notebook storage files directly. Remote report content must first be validated and rebuilt from the report schema; arbitrary Markdown from an SSH peer must not be imported automatically.

Notebook pages are presentation, not authorization or the active policy. The documented interface does not establish a secure privileged button/action bridge. Live schedule changes, exceptions, report requests, and time grants must remain in the Family Lab UI/CLI through the separately authenticated policy/report endpoints. A displayed policy snapshot must show its revision and capture time, and cannot imply live status. Editing a note must never apply a child policy. Notebook availability must never affect enforcement.

## Optional ActivityWatch provider

The separate [upstream integration adapter](OPTIONAL_INTEGRATIONS.md) can now read
selected local ActivityWatch browser, active-window and idle buckets on demand instead
of requiring a manually imported snapshot. It does not install a tracker or enable
collection itself. Setup requires explicit raw-data acknowledgement and preserves
separate report-only SSH enrollment. Existing imported reports remain the default.
