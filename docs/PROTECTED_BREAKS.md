# Protected breaks and bedtime

This module preserves the learner's open desktop. It uses 60 minutes of awake logged-in use followed by a 15-minute break by default. It is not a daily allowance. Idle time and ordinary password locks count as use; protected Dino time does not. Logout/reboot does not reset accumulated use. The break countdown starts only after the trusted Wayland lock acknowledges protection.

## Enrollment

Use the existing reviewed household profile; never commit its addresses, names or keys. On the enrolled parent desktop run:

```sh
./master-installation.sh controls --role helper --profile /private/enrollment.json
```

Copy the resulting profile and current source bundle through the separate administrator. On the learner PC:

```sh
sudo ./master-installation.sh controls --role learner --profile /private/enrollment.json --enable-pam --activate
```

Existing reviewed installations may require `--adopt-existing`; private backups and drift checks remain in place. This is an explicit follow-on module, not an automatic part of the primary enrollment wizard. A repeat run refuses currently enforced policies or an active guard. Switch policies off and release the guard first. Do not run the primary helper installer over a controls-enrolled desktop without reconciling its generated configuration.

New policies remain **off**. Set the timezone, allowed hours and break durations in **Family breaks and bedtime**. Parent policy access uses an independent forced SSH identity and cannot open a shell, approve software, authenticate as the learner, or administer the machine. Only actually enrolled helpers appear on Dino's screen. Both technical and approval-only parents have the same time controls.

## Live acceptance before enforcement

Keep a verified administrator connection and local recovery available. The root-only local request `{"op":"guard-trial","peer":"LEARNER_ID","seconds":60}` tests protection with the regular policy off. It automatically restores the prior usage state, allows 15–600 seconds with a watchdog two minutes beyond the requested duration and expires across reboot. Confirm the Dino screen covers every display, open work survives, normal desktop input is blocked, and Return to my work restores that work. Verify the separate administrator remains accessible and learner login is denied during protection.

The root-only `{"op":"accept-guard","peer":"LEARNER_ID"}` requires a recent same-boot secure-lock and fresh-release receipt. It records installed source hashes; changed guard sources invalidate acceptance. Only then can a parent enable enforcement. Automated fixture tests are not this live acceptance.

## One-shot parent decisions

A learner may ask an enrolled parent to skip, shorten or extend the current break. Requests do not pause the countdown. Each request is bound to a particular break and revision, expires after 15 minutes and can be decided only by its intended parent. A stale or conflicting approval cannot change a later break. A parent may also adjust the current break directly in their controls window.

Bedtime is independent. **Skip bedtime today** expires at midnight in the policy timezone; **Restore bedtime today** cancels it early. Neither action skips a break. Changing a break never bypasses bedtime. Native account password locks remain separate; the Dino guard has no password field and offers Return to my work only after a fresh allowed-status check.

## Reporting and recovery

### Bedtime hibernation

The bedtime card includes **Hibernate now** and a five-minute automatic hibernation countdown. This applies only outside allowed hours on an explicitly accepted, dedicated single-learner PC. Ordinary breaks never hibernate. A parent bedtime exception or policy change cancels the pending action. The countdown is persisted by the root service: restarting the UI/service does not grant another five minutes. A genuine wake, detected from the difference between Linux boot and monotonic clocks, starts a fresh five minutes if bedtime still applies.

The isolated guard sends only a fixed bedtime request bound to the current episode. It receives no sudo rights or general power commands. Root rechecks current policy and a recent secure-lock acknowledgement before requesting logind Hibernate; it does not bypass inhibitors. Failure keeps the lock and displays an error, with retries limited to once per minute. There is no logout, shutdown or suspend fallback.

New and upgraded installations do not enable power actions automatically. After testing the newly installed protected guard, perform a real hardware hibernate/resume test with an administrator present. Check that all displays stay protected and open work survives. Only then may local root send `{"op":"accept-hibernate","peer":"LEARNER_ID"}`. This requires accepted guard source hashes and logind capability; it records the administrator's explicit hardware-test confirmation, not an automatic proof of successful resume. Removing `/etc/family-lab/hibernate-ready` disables this end action. Existing break/bedtime locking remains independent of this marker. Changed guard sources require fresh guard acceptance before recording hibernation acceptance.

Private reports contain sampled awake logged-in totals excluding protected Dino time. They do not collect applications, websites, screenshots or attention. Missing data is not proof of no use.

For a healthy service, use the parent controls to switch enforcement off, then click Return to my work before stopping or upgrading the service. Do not kill the guard as a normal unlock method. Compositor lock restoration must be enabled; Omarchy's stock configuration provides it. A crashed guard is restarted under its isolated account while policy still blocks access. The legacy `recover` command stops the service and clears policy gates, but a compositor lock may remain after its process is stopped; preserve a separate administrator/console recovery route. Never terminate the learner's session merely to clear a break.

## Validation status

Existing-household protected-break acceptance passed on 2026-10-18: the protected screen blocked desktop use, parent denial kept it protected, a new parent-approved skip allowed fresh release, and the learner returned to intact open windows. Learner login was denied during the test and the separate administrator gate remained allowed. Parent extend/shorten and same-day bedtime skip/restore were checked. Bedtime hibernation now has isolated timer, authority, failure and wake tests; these do not replace its separate hardware acceptance. Clean enrollment of a second parent and post-enforcement reboot remain pending. Application/browser activity collection is outside this module.

The parent controls use a floating top-right popup with compact monospace styling. Both this popup and the Ask Dad cards share a palette mapped to the local active Omarchy theme. Open popups refresh their colors within a few seconds after theme changes. Missing or malformed theme data falls back to the established dark blue, teal and cyan colors. Action buttons live in a fixed footer while settings scroll above, keeping them reachable on smaller displays. Controls enrollment installs a narrowly matched user Hyprland rule; reload and inspect configuration errors after changing it. These desktop changes do not modify the protected guard or its accepted source hashes.
