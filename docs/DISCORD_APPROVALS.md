# Private Discord approval fallback

The edge bot is an adapter to existing approval services, not an administrator.
It uses outbound Discord Gateway connections: no public webhook, router port
forwarding, message-content intent, member intent or presence intent is needed.

## Behavior

- Native Omarchy approval cards remain first. Unanswered requests are eligible
  after 180 seconds. Polling can add about 15 seconds.
- A heartbeat-only desktop key reports availability every 20 seconds while the
  existing Ask Dad watcher is active. After an observed desktop's heartbeat is
  60 seconds stale, pending requests can escalate earlier. Unknown availability
  waits the full three minutes. This is an availability estimate, not instant
  detection that a machine lost power.
- Only the configured Discord server, channel and exact parent user IDs can
  operate the controls. Server roles alone grant no decision authority. Only the
  requesting Dad identity is mentioned; broad mentions are disabled.
- App requests show the reviewed title and pinned package transaction. Unsupported
  or overly large plans have no Approve button. The existing app broker rechecks
  the plan, digest, expiry and one-shot receipt before queuing an install.
- Break decisions retain the source episode/revision and expiry checks. They
  cannot edit schedules, change bedtime, grant arbitrary time or open a shell.
- Learning topics support approve, decline and a change-topic modal. The companion
  DeepTutor feature stores the original topic and records the revised subject.
  Approval does not call AI, generate or publish a course, assign work, or unlock
  a website. Parent authoring/review/assignment remain separate actions.
- Bedtime/screen-time help is informational. **Mark seen — no time granted**
  acknowledges the notification locally; it does not settle a policy request or
  close the native help card. Actual time changes require the parent controls.

Source services remain authoritative. A desktop decision wins if it reaches the
source first; stale Discord controls cannot replay it. Native topic cards close
when the source topic is no longer pending. Losing a connection gives an
unconfirmed result, never an assumed approval. Discord action cards expire after
15 minutes; older topic ideas can still be reviewed in Family Learning.

## Deployment prerequisites and private configuration

Use a separate always-on, administrator-managed Linux edge host. Python 3.12 and
`discord.py==2.7.1` were used for this deployment. Install into a dedicated venv;
the service needs neither Docker group membership nor a Docker socket. The bot's
token must be entered privately and kept outside Git. A bot token is different
from the application public key and client secret.

Create a private server/channel accessible to the parents and bot. Disable Public
Bot and privileged intents; set the installation link to None before making the
bot private. Invite with `bot` and `applications.commands` scopes and only View
Channel, Send Messages, Embed Links and Read Message History permissions. Register
the exact server, channel, application and parent IDs in root-only configuration.
The child needs no Discord account and no access to the approvals server.

The root-only `/etc/family-lab-discord/config.json` contains `application_id`,
`guild_id`, `channel_id`, `parents` (`dad` and optional `mom` user-ID strings),
`learner_host`, `escalation_seconds: 180`, and boolean `enabled`. Start disabled.
Store the token as `/etc/family-lab-discord/bot-token`, mode 0600, directory 0700.
Use systemd `LoadCredential` entries named `token`, `config`, `transport` and
`hosts`; do not pass secrets in command arguments or environment variables.

Install the reviewed source modules from `integrations/` into a root-owned
directory, with `family_discord_bot.py` as `bot.py` and
`family_discord_pending.py` beside it. The service runs with `DynamicUser=yes`,
`StateDirectory=family-discord-relay`, `NoNewPrivileges=yes`, `ProtectSystem=strict`,
`ProtectHome=yes`, a private temporary directory, and only INET/INET6/UNIX address
families. Start it in setup mode and verify `/relay-test` approval and denial
before enabling real requests. This command changes no family state.

## Restricted source transports

Generate a new unattended relay key on the edge. Do not copy any parentadmin,
policy or provider key. Pin the child's already verified public SSH host key.
Never disable host-key verification. The current adapter uses these dedicated
forced endpoints:

| Account | Allowed operations |
| --- | --- |
| `familyap-discord` | Existing reviewed app scope: poll, prepare, status, decide |
| `flpolicy-dad`, only from the edge IP | break-pending, break-status, break-decision |
| `familytopics-discord` | topic-pending and bounded topic-decision |
| `familytopics-dad`, only from Dad's IP | Native topic review; fixed Dad identity |

The app relay principal is separate from Dad's app principal so preparing its
review cannot overwrite a desktop review. Copy only the existing reviewed app
scope into that principal, not technical-admin privileges. The current break
adapter uses the existing Dad policy identity, narrowed by a source-specific
forced command; root policy audit therefore labels it Dad while the bot journal
records which enrolled Discord parent acted. A future independent Mom native
route needs separate enrollment, not a shared administrator key.

Install `family_discord_bridge.py` root-owned and source-restrict its public key.
It permits only its assigned app/break operation schema and forwards bounded JSON
to the existing local Unix socket. The source service still authorizes the peer
UID. Deny PTYs, passwords, user startup files, agent and TCP forwarding, arbitrary
commands and user-owned authorized-key overrides. Check `sshd -T -C` output with
case-insensitive setting names and test the effective result, not only file text.
Keep the existing Dad keys and registry entries.

The topic wrapper `family_discord_topics` is the only allowed sudo command for
the topic accounts, with **no arguments**. Validate its sudoers fragment with
`visudo -cf`; no generic Python, Docker or shell command may be permitted. It
accepts only fixed topic metadata/decision operations and invokes the companion
DeepTutor `topic_requests_cli` as the managed app service UID. It cannot call
general app/AI/admin APIs. Preserve the container's internal network and mounts.

If the child's firewall restricts SSH by source, add only the edge IP to the
child's SSH port on the home interface. Do not flush rules or expose other ports.
Validate actual edge-to-child connectivity before starting live polling.

## Desktop heartbeat and topic cards

Use a second key, generated on the parent desktop, for heartbeat only. On the
edge, its authorized-key line must source-restrict the parent IP and force
`family_discord_heartbeat.py` under a non-admin execution path. This script
accepts only the fixed heartbeat JSON and updates a pre-created regular file
under root-owned `/var/lib/family-discord-heartbeat/`. No caller path, timestamp
or command is accepted. The bot reads its `parent.json` timestamp. The key must
not obtain a shell or make decisions.

Run the desktop heartbeat only while `family-help-watch.service` is active.
Install `family-topic-watch` alongside the existing `family_theme.py` helper.
Its private `~/.config/family-help/topics.json` selects the verified child host,
`familytopics-dad` account, a separate topic-only key and pinned known-hosts file.
Start it in the graphical user session, never root. It polls the topic-only
endpoint and uses the shared Omarchy theme. It has no application password or
provider token. The learner's normal web session submits the topic.

Topic cards use the dedicated `org.familylab.HelpTopics` app ID and a compact
620×340 layout. Install `integrations/family-topic-popup.lua` into the parent's
user Hyprland configuration and load it from `hyprland.lua` after Omarchy's
defaults. This precise rule floats and centers only topic cards, not Dino or
other help windows. Reload Hyprland and check `hyprctl configerrors`. The shared
`family_theme` helper refreshes colors when Omarchy's palette changes. Run
`family-topic-watch --preview` to inspect the themed card without polling or
submitting a decision; its approval controls are disabled.

These are reviewed operator deployment steps; the master enrollment wizard does
not yet automate Discord token setup or edge enrollment. Keep private staging,
configuration, key files, activity data, app images and backups outside Git.

## Acceptance record and rollback

Live household checks performed October 27, 2026:

- [x] Bot identity and private channel access; setup approve/deny buttons.
- [x] New app request: three-minute escalation, Discord denial, learner denied status.
- [x] Simulated unavailable desktop: heartbeat stopped, earlier card, denial confirmed;
      heartbeat restored immediately afterward. Physical power-off not separately tested.
- [x] Real break: Discord denial retained Dino lock; new approved skip enabled Return
      to my work.
- [x] Learning topic: native card appeared; Discord changed and approved the subject;
      learner saw the revised topic. No course was automatically assigned.
- [x] Native topic denial suppresses Discord escalation and learner sees declined.
- [x] Informational bedtime-help delivery/acknowledgment; no extra time granted.
- [x] Synthetic tests against deployed bot reject non-parent/wrong-server/wrong-channel.
- [x] Actual restricted break transport rejects a pause/schedule operation.

The synthetic tests never install software, change policy or send messages.
Delivery claims are durable. A crash after claiming but before recording delivery
can leave an unsent card rather than risk duplicate notices; review the source
on the desktop and send a new request in that case. This is not guaranteed
exactly-once Discord delivery. Keep journal and state private; do not log tokens
or full API error bodies.

To stop Discord fallback, stop/disable the bot service and the desktop heartbeat;
native approvals and source policy continue independently. Revoke the dedicated
relay/topic/heartbeat keys to revoke remote access. Preserve source accounts,
coursework and existing Dad keys. Reverting an app update uses its recorded
previous container and private data backup. Never erase data volumes as part of
disabling this adapter. No changes to Pi-hole or household DNS are required.
