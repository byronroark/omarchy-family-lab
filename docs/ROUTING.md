# Multiple helpers: ask-dad, ask-mom and forwarding

Helper and learner are independent roles. Mom and Dad can each help a learner from their own PCs, and an adult helper can also request help with their own learning. No role is tied to a spouse, gender, machine inventory or administrator privilege. Public examples use generic learner IDs; real names, addresses and keys stay local.

## Workflow

```text
learner: ask-dad "Please help with this command"
                     |
                     v
Dad's notification -> click -> Open terminal / Ask Mom / Close
                                               |
                            separate authenticated relay key
                                               |
                                               v
Mom's notification: learner-a (via dad) -> read-only terminal

learner: ask-mom "Please help with this command" -> Mom directly
```

`ask-dad` and `ask-mom` select one destination each. There is no automatic broadcast, timeout escalation or silent failover. `family-lab ask <helper-id> "message"` supports other locally configured helper IDs. The original single-helper `notify_alias` remains a fallback for Dad only; a missing Mom route fails explicitly instead of silently sending to Dad.

The inspected native Omarchy notification has one click command, and its card handles the default action rather than rendering extra action buttons. Where forwarding is enrolled, clicking the notification opens a **Zenity menu** with **Open terminal**, **Ask Mom** (or another configured helper), and **Close**. The menu is the native-backend implementation, not inline buttons on the stock toast. Without forwarding choices, clicking still opens the read-only terminal directly. The optional [experimental inline plugin](INLINE_UI.md) now renders Open terminal/Ask Mom/Dismiss directly on a separate themed Family Lab card using inspected Omarchy 4.0 APIs. The native backend described above remains the default and fallback.

Forwarding asks another helper to look at the same help request. It does not approve a command, grant administrator access, enroll a key, transfer control, or confirm that anyone has read the request. Mom opens a read-only view and can request optional control using her own key; the learner approves that specific connection separately. Only one control connection can be pending/active at a time. If Dad currently controls the terminal, he must disconnect or the learner must revoke him before Mom requests control.

## Enroll direct routes

Install/review the current script on each participating desktop account as described in INSTALL.md and CONTROL.md. An upgrade must deliberately replace the reviewed user command; then run the installed `family-lab install` as that same user to add the new `ask-mom` symlink without replacing local config. Do not overwrite the existing config with an example.

On the learner PC, create **two independent notification-only keys**: one to Dad, one to Mom. Each destination desktop account enrolls only its corresponding public key with the existing `restrict,from=...,command="... receive learner-a"` pattern. Configure independent local SSH aliases using the real destination address, account and key. Compare host fingerprints at each console. Example learner config fragment:

```json
"notify_aliases": {
  "dad": "family-dad-notify",
  "mom": "family-mom-notify"
}
```

See [learner configuration](../examples/learner.config.example.json) and [SSH templates](../examples/ssh-config.example). Both Dad and Mom run their own graphical `family-lab watch`. Each has their own `view_aliases` and viewing key for the learner. Mom's PC is a helper endpoint, not an automatically managed standard-user PC. She retains her own full privileges. Child account restrictions apply to the child separately.

For optional hands-on help, enroll **independent Mom and Dad control keys** on the learner PC. Name their forced endpoints so the learner sees which enrolled key is requesting access:

```text
from="<dad-source-address>",restrict,pty,command="/home/<learner-login>/.local/bin/family-lab control dad" <dad-control-public-key-line>
from="<mom-source-address>",restrict,pty,command="/home/<learner-login>/.local/bin/family-lab control mom" <mom-control-public-key-line>
```

The helper ID is fixed by each key's forced command. Labels such as **MOM CAN TYPE** identify the enrolled key role, not proof of the human at the keyboard. Legacy `control` entries without a name keep the generic Helper label. Follow CONTROL.md for each helper's separate control alias and local approval. Neither helper receives administrator rights on the learner PC through this feature; separate administrator enrollment is a distinct decision.

## Enroll Dad → Mom forwarding

Forwarding is disabled by default. Verify the installed Zenity supports question dialogs, `--extra-button`, `--no-markup`, and the expected return values. Do not change the packaged Omarchy notification service. The action menu and real desktop routing must pass the deployment gates before use.

Generate a **new dedicated relay key on Dad's PC for this learner**. It is separate from learner notification keys, viewing/control keys and admin keys. An unattended key is acceptable only with the narrow forced command and source restriction below. Mom must agree to receiving these requests. Mom enrolls its public key in her desktop account's authorized_keys:

```text
from="<dad-source-address>",restrict,command="/home/<mom-login>/.local/bin/family-lab receive-forward dad learner-a" <dad-to-mom-learner-a-relay-public-key-line>
```

This key fixes **both the forwarding source and learner**; it cannot select another learner, run commands, allocate a PTY, forward ports, or open a terminal on Mom's PC directly. Use a separate key/entry for each additional allowed learner. Confirm no unrestricted duplicate of that key exists.

Mom's local config must explicitly authorize that source/learner pair and map that learner to her own viewing alias:

```json
"relay_sources": {"dad": ["learner-a"]},
"view_aliases": {"learner-a": "family-learner-a-view"}
```

Dad's local SSH config gets an alias such as `family-mom-learner-a-relay`, pointing to Mom's host and desktop login and this relay private key. Use `IdentitiesOnly yes`, strict host checking, no agent/X11 forwarding and no configured port forwards as in the templates. Dad's local config fragment:

```json
"forward_routes": {
  "mom": {"learner-a": "family-mom-learner-a-relay"}
}
```

See separate [Dad helper](../examples/dad.config.example.json) and [Mom helper](../examples/mom.config.example.json) templates. These are synthetic examples; merge only intended fields into local config. Dad's route and Mom's relay enrollment are both needed. For another direction, enroll another scoped key and mappings deliberately; nothing is automatically reciprocal.

Adjust the existing firewall for the actual flows: learner → Dad SSH, learner → Mom SSH, Dad → Mom SSH for relay, and each authorized helper → learner SSH for viewing/control. Scope each to reserved addresses, including IPv6. Keep all host keys verified and do not expose SSH through the router.

## Retries, expiry and failure

Each direct request gets an opaque request ID at its receiver. Relay preserves that ID, original text and ten-minute expiry. Mom labels it **via dad**: the relay key authenticates Dad's attestation of the learner, not a fresh cryptographic signature by the child. Do not trust message text as sender identity.

A relayed request cannot be forwarded again. One-hop routing prevents Mom/Dad loops. A repeated click after successful forwarding is a no-op. Lost SSH acknowledgements can be retried: Mom deduplicates the same ID/content instead of showing it twice. Reusing an ID with different content/source/learner is rejected. Forwarding never refreshes the lifetime.

Original requests remain available on Dad's side until expiry. If Mom is offline or a route fails, the forwarding attempt reports failure and does not mark the request forwarded; retry while it is live or contact each other directly. A queue acknowledgement is never a read receipt. There is no globally exclusive help assignment: Dad can still view, and the learner can make separate requests directly. Coordinate before editing; optional control remains single-connection.

Each helper keeps at most 20 live request records for up to ten minutes, including delivered requests retained for click actions. Input and cooldown limits still apply. Entries are pruned when the watcher, receiver or inbox/action commands run; files may remain on disk longer while every command is stopped. State is private to that desktop user and not an encrypted archive. Do not commit it.

Recovery commands in a local helper terminal:

```sh
family-lab inbox
family-lab request <request-id>
family-lab forward <request-id> mom
```

The first lists local request IDs and routing status without printing message bodies. The second reopens the local action menu; the third explicitly retries a configured route. An expired ID cannot be reopened or forwarded. Stop the watcher and remove only scoped relay key entries/mappings to disable forwarding. Removing the relay key does not remove Mom's independent view/control keys; revoke those separately if desired.

## Deployment acceptance

Test actual `ask-dad` and `ask-mom` destinations, verified independent keys, Mom's watcher and learner mapping, Dad's click menu and **Ask Mom** action, Close/Escape without forwarding, offline/failing relay, retry/deduplication, original expiry, source/peer spoof rejection, no second-hop loop, distinct named control approvals, and existing revoke behavior. Confirm a help request never approves privileged commands or grants control by itself. GUI choices and transport mapping have hermetic tests, but a real multi-PC notification/menu/SSH acceptance run is still required.
