# Optional consented terminal control

The normal help notification still opens a read-only view. Control is an additional, opt-in path with a separate SSH key. It permits editing commands and running them as the learning account after approval on the learner’s PC. It does not grant administrator rights or connect an AI automatically.

## Enrollment

Complete the base read-only installation and its acceptance gates first. Update the reviewed installed command on both ends before adding control keys. The user installer intentionally refuses to overwrite an existing file: stop sharing/watcher, back up the existing `~/.local/bin/family-lab` outside this repository, review the diff, and deliberately replace that one file with the new `scripts/family-lab` (owner-only mode 700). Existing config is preserved; add the optional mapping manually. Never copy local configuration into this repository.

Generate a new passphrase-protected **control-only** Ed25519 key on the helper PC. Do not reuse viewing, notification or administrator keys. Verify the learner’s host key through the already established trusted channel. The learner or authorized parent enrolls only its public key in that learner account’s authorized_keys:

```text
from="<helper-source-address>",restrict,pty,command="/home/<learner-login>/.local/bin/family-lab control" <actual-control-public-key-line>
```

Use real local values, correct permissions, verified source addresses and the base installation’s SSH/firewall restrictions. Keep this key distinct so it can be removed without disabling read-only assistance. Audit duplicate unrestricted entries. The forced command ignores SSH_ORIGINAL_COMMAND: the key cannot choose `allow-control`, arbitrary commands, SFTP or forwarding.

On the helper, add a local alias:

```sshconfig
Host family-learner-a-control
    HostName <learner-a-address>
    User <learner-a-login>
    IdentityFile <absolute-control-private-key-path>
    IdentitiesOnly yes
    ForwardAgent no
    ForwardX11 no
    ClearAllForwardings yes
    StrictHostKeyChecking yes
```

Add to the helper’s local `~/.config/family-lab/config.json`, retaining other settings:

```json
"control_aliases": {
  "learner-a": "family-learner-a-control"
}
```

The above is a fragment inside the existing JSON object. Fresh installs default to an empty control mapping. Each additional learner has an independently agreed key and alias. Adult learners keep their own administrator privileges and decide whether to enroll a control key at all.

## A hands-on session

1. Learner runs `family-lab learn` and sends the usual `ask-dad "message"`. Helper opens the read-only notification and discusses the intended change.
2. Helper loads the control key with `ssh-add <absolute-control-private-key-path>` and runs `family-lab assist learner-a` in a separate terminal on their own PC. The ordinary viewer can remain open and stays read-only.
3. A single control connection attaches **read-only while waiting**. The learning terminal shows a yellow control-request status. It expires after 60 seconds if not approved. There is no writable connection merely because the helper asks.
4. In the local learning shell, or another local interactive terminal on the learner PC, learner runs `family-lab allow-control`. They read the warning and type exactly `yes`. Any other answer declines and disconnects the request. Piped input and ordinary SSH-based approval are rejected. Approval applies only to this pending connection; a delayed answer cannot approve a newer reconnect.
5. Once enabled, the learning terminal has a red **HELPER CAN TYPE** status. The helper can edit the shell’s current command line, type commands and interact with terminal programs. Both people share the terminal, so coordinate turns to avoid mixing input. Default approval is five minutes. `family-lab allow-control 60` instead grants one minute; allowed durations are 1–300 seconds.
6. To revoke, learner presses **Ctrl+B, then Ctrl+R** inside the learning terminal. This shortcut belongs only to the dedicated tmux server and works while a foreground program is using the shell. Alternatively run `family-lab revoke-control` from another local terminal. The control connection is disconnected; ordinary viewers and the learning session remain. `family-lab stop` ends all sharing and running learning jobs.

A reconnect always starts pending/read-only and requires another approval. Expiry disconnects the control client. Linux boot-time deadlines include suspend; on resume the supervisor revokes an expired grant on its next scheduling pass. Closing/detaching the learner terminal is still not revocation. A stale red indicator after a supervisor crash can be cleared with `family-lab revoke-control`; do not interpret a frozen display as live connection status.

## Helping with AI from the helper PC

Use your own AI to interpret a non-sensitive error or prepare a suggested command. Review its explanation and command before typing into the approved shared terminal; explain what you are about to run. No automatic terminal-output upload, AI execution bridge, credential sharing or autonomous AI control is implemented. Never ask an AI to approve its own access. Privileged administration stays in a separately authorized, unshared administrator session.

## Trust model and limits

This is cooperative assistance for a **trusted helper**, not a sandbox against a hostile controller. The initial forced control connection cannot type or approve itself before consent. Once approved, the helper has the learning account’s shell capabilities: reading/changing files, running programs, changing tmux/configuration and potentially establishing persistence. On an administrator’s account that can include anything that account’s existing privileges permit. The prototype does not technically block sudo; do privileged work elsewhere and never supply passwords here.

Revocation/expiry cuts off this managed tmux client’s future terminal input; it does not undo edits, terminate already-started jobs, cancel commands already queued, clear partially typed commands or revoke other access a malicious helper might establish. Inspect the current command line after revocation before pressing Enter; Ctrl+C can cancel an unwanted partial command. If trust is broken, stop sharing, terminate suspect jobs/access and recover the account separately. Strong isolation requires a disposable account/VM with limited files and credentials.

The local confirmation check is a usability guard, not proof of a particular human’s identity. Same-user software and already-approved controllers are trusted and can tamper with files or controls. The registered PID, process start time, boot identity and client name prevent accidentally targeting a recycled/stale client; they are not isolation from that account owner.

The Linux supervisor serializes one control connection, monitors consent/deadlines, and removes permission before detaching on normal revocation. Its child tmux client has a parent-death signal so abrupt supervisor exit also kills that client. This covers accidental supervisor death; not a hostile helper changing the environment or account. Tests cover local PTY/tmux behavior, not all SSH/network/desktop deployments.

## Acceptance before use

Verify both key types independently: view remains read-only during control; control waits for local approval; SSH/piped approval is rejected; wrong/absent key and forwarding fail; only the correct peer opens; decline, stale approval and pending timeout disconnect; red status precedes input; the learner shortcut revokes during a foreground job; expiry, helper disconnect, reconnect, supervisor crash and stop behave as documented. Test suspend/resume on the deployed PCs. Check normal user privileges and local recovery. Record only sanitized results.
