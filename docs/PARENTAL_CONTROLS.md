# Optional parental controls — implementation sequence

This is the agreed direction, not a claim that enforcement exists. Adults can use assistance without enrolling in parental controls. Every future module starts off. No web frontend is required.

| Stage | Scope | Current state |
| --- | --- | --- |
| Reporting foundation | Private Markdown, imported observations, report-only SSH, optional LocalSend | Experimental implementation; see REPORTING.md |
| Policy management | Child-local authoritative revision, separately enrolled parent keys, stale-edit rejection, validation, rollback | Planned |
| Activity collection | Visible desktop collector, idle/lock/suspend handling, opt-in browser domain adapter, coverage gaps | Planned |
| Monitoring | Persistent daily accounting, remaining-time display, warnings; no restriction | Planned |
| Screen-time enforcement | Allowed hours, daily budget, temporary extensions, login/session integration, recovery | Planned; requires real Omarchy acceptance tests |
| Content filtering | Optional DNS backend, managed browser policies, exceptions and SafeSearch where supported | Planned; backend evaluation required |
| Application rules | Supported app restrictions, independently enabled | Later; effectiveness must be demonstrated |
| Parent/learner UI | Theme-aware forms, schedule, more-time requests, site exceptions, report preview, undo | Planned; existing inline assistance buttons remain separate |

## Architecture to preserve

The child's PC stores an administrator-owned active policy and enforces it independently of parent availability. Mom/Dad keep local snapshots and submit authenticated changes against a base revision. Conflicting updates require review; no last-writer-wins folder sync. Policy and report authority are distinct from terminal/admin credentials. No policy file may contain commands to execute as root.

The privileged enforcement component must remain small, expose fixed validated operations, preserve a known-good policy atomically, and have documented local administrator recovery. Policy keys, household configuration, detailed observations, reports, and usage state stay out of Git. Device usage counters are not synchronized policy settings.

The standard child account must lack sudo/wheel, permissive polkit grants, and Docker-daemon access that could bypass controls. Assistance that gains the child's shell can modify user-owned reporting observations; this reporting foundation is not audit evidence. Future trusted collection needs an explicitly reviewed trust boundary.

Before enabling screen-time enforcement, test logout warnings/unsaved work, immediate relogin prevention, reboot/suspend accounting, timezone and clock changes, policy corruption, offline parents, and recovery. A lock screen alone is not enforcement. Unsupported collectors and missing data must never be represented as zero use.

DNS requests are not page visits or attention. Browser/domain observation and application time must avoid double counting. No covert collection, HTTPS interception, message/keystroke capture, or automatic AI upload is planned. Retention, deletion, and access audit are required before automatic collection is deployed.
