# Enrolling another parent with Family Manager and DeepTutor

A parent's operating-system assistance role and tutoring role are independent.
Choose **Mom → approver** for reviewed app approve/deny cards, and enable
**break and bedtime approval controls** and **Family Learning and personal parent
AI course authoring**. The parent receives separate scoped approval and policy
keys, plus a DeepTutor parent application account. No administrator private key,
Linux password, other parent's OAuth login or child work is copied to her PC.

## Existing host prerequisite

This workflow connects to an **already installed, managed DeepTutor host on the
child's PC**. It does not download or install DeepTutor, Docker, an arbitrary AI
provider, or a model on the parent's computer. The host must already provide the
full parent dashboard and LAN listener on port 3785 with login enabled, the
local learner boundary enabled, and its exact LAN origin configured. Initial
DeepTutor server installation remains the separate, reviewed host installer in
byronroark/DeepTutor. Missing or incompatible servers stop enrollment safely;
the wizard does not replace existing accounts or data.

The existing child policy service must advertise `parent_enrollment_reload`
before a second controls parent can be added while enforcement stays active.
Older hosts need a reviewed policy-service upgrade in a maintenance window;
never copy an older policy program over a newer hibernation implementation.
The additional-parent phase changes parent routing and scoped SSH credentials,
not the child's policy, active guard, hibernation acceptance or saved schedule.

## Parent desktop phase (without sudo)

Use the same stable learner ID as the existing child enrollment, and a distinct
parent ID such as `mom`. Verify the child's SSH host fingerprint independently.
Run on the new parent's own desktop:

```sh
./master-installation.sh configure
./master-installation.sh plan
./master-installation.sh apply --activate
./master-installation.sh bundle --out "$HOME/family-mom-enrollment"
```

The configure wizard asks about assistance role, break controls and tutoring.
The helper phase generates her independent restricted keys, pins the learner
host, installs request cards and the Family Manager bar launcher, and adds
**Family Learning**, **DeepTutor parent dashboard**, **Connect my tutoring AI**
and **Family Manager setup** app launchers. `--activate` places the bar widget
only in the logged-in parent's session and backs up the existing bar layout.
Without it, files are staged; rerun apply with `--activate` in that session.
Existing profiles omit these new options by default; configuration is not
silently expanded during an unrelated reapply.

## Technical administrator phase on the child PC

Transfer the generated directory through the existing trusted administrator
connection to an administrator-owned private location. The new parent does not
need that administrator's credentials. Review the plan before root application:

```sh
./master-installation.sh plan --profile /private/family-mom-enrollment/enrollment.json
sudo ./master-installation.sh apply --role learner --approval-only \
  --profile /private/family-mom-enrollment/enrollment.json
sudo ./master-installation.sh verify --role learner --approval-only \
  --profile /private/family-mom-enrollment/enrollment.json
```

This preserves the technical parent's existing access and registers the new
parent's scoped approval and controls endpoints. Tutoring enrollment verifies
the existing managed container and learner boundary. It creates the configured
DeepTutor parent account using private password prompts, or preserves an
existing parent account with that name. It refuses to promote an existing
learner account. The application password is separate from Linux passwords.

If selected, firewall enrollment requires active UFW and discovers the child's
exact interface by its configured LAN IP. It adds incoming SSH and DeepTutor
rules only from the new parent's exact IP to the child's exact IP. It does not
enable/disable UFW, flush rules, create router forwarding or open all ports.
Existing broader household rules are not narrowed by these additive rules.
Reserve device addresses in DHCP before enrollment.

Enrollment phases are checkpoints, not one global transaction. A later-phase
failure can leave earlier approval enrollment in place. Preserve the bundle,
read the failure, correct the prerequisite and rerun; do not delete credentials
or private application data. Existing controls enforcement is never disabled to
make enrollment proceed. Do not use `--approval-transport-only` for the complete
workflow: that flag deliberately skips controls and tutoring.

## Private AI sign-in and acceptance

On the new parent desktop, open **Family Manager setup**. Sign in to DeepTutor
with her own parent application account. Open **Connect my tutoring AI** and
complete her own ChatGPT/Codex connection. Authorization requires her private
browser interaction; the installer cannot sign in on her behalf. If localhost
callback forwarding is unavailable, finish through DeepTutor's manual callback
address field. Keep callback addresses out of chats, enrollment files and Git.

Select an available model, generate and review a draft, check Python reference
programs, publish privately, then assign a chosen course. No course is assigned
automatically. Other providers need separately reviewed network access; this
household's host currently permits only the configured OpenAI destinations.

Run helper verification after the administrator phase. It checks strict SSH
settings and DeepTutor reachability with authentication enabled. Then perform
these live checks; installation success alone does not prove them:

1. Deny a new app request; send a separate request and approve an in-scope app.
2. Deny and approve separate child break requests using Mom's new card.
3. Confirm the existing bedtime/break policy and Dad's access still work.
4. Confirm Mom sees the parent dashboard, while Odin remains in Family Learning
   and cannot open provider, authoring or general AI endpoints.
5. Connect Mom's own AI account, generate/review/publish a private sample, assign
   it explicitly, and run a learner coding exercise.

The child's PC must be awake for its DeepTutor server and approval endpoints.
Mom does not need Docker, sudo, Dad's private key or an always-running copy of
DeepTutor on her own desktop.
