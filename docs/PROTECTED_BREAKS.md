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

Private reports contain sampled awake logged-in totals excluding protected Dino time. They do not collect applications, websites, screenshots or attention. Missing data is not proof of no use.

For a healthy service, use the parent controls to switch enforcement off, then click Return to my work before stopping or upgrading the service. Do not kill the guard as a normal unlock method. Compositor lock restoration must be enabled; Omarchy's stock configuration provides it. A crashed guard is restarted under its isolated account while policy still blocks access. The legacy `recover` command stops the service and clears policy gates, but a compositor lock may remain after its process is stopped; preserve a separate administrator/console recovery route. Never terminate the learner's session merely to clear a break.

## Validation status

32 local regression suites passed, including a disposable nested Hyprland lock, locker crash/recovery, unhealthy-status refusal and fresh-permission release. Installer tests stage all writes and intercept privileged operations, including repeat-run checks. Existing-household live acceptance passed on 2026-10-18: the protected screen blocked desktop use, parent denial kept it protected, a new parent-approved skip allowed fresh release, and the learner returned to intact open windows. Learner login was denied during the test and the separate administrator gate remained allowed. Parent extend/shorten and same-day bedtime skip/restore were checked. The accepted source hashes were recorded, enforcement enabled and healthy status verified; private report generation also passed. A real overnight bedtime transition and post-enforcement reboot remain untested. Clean enrollment of a second parent remains pending until that PC is available. Hardware hibernation and application/browser activity collection are outside this module.

The parent controls use a floating top-right popup with compact monospace styling. The palette matches the established Ask Dad cards (dark blue, teal and cyan). Action buttons live in a fixed footer while settings scroll above, keeping them reachable on smaller displays. Controls enrollment installs a narrowly matched user Hyprland rule; reload and inspect configuration errors after changing it. These desktop changes do not modify the protected guard or its accepted source hashes.
