# Contributing

Small, reviewable changes are welcome. Discuss changes to consent, key permissions, session behavior or transport before implementing them. Keep remote administration separate from assistance.

## Local checks

From the repository root:

```sh
python3 -m py_compile scripts/family-lab
bash -n scripts/preflight.sh
python3 tests/check_receiver.py
python3 tests/check_routing.py
python3 tests/check_inline.py
node tests/check_ui_model.cjs
python3 tests/check_tmux.py
python3 tests/check_control.py
```

Tests use temporary homes and an isolated tmux socket. The tmux check needs tmux, a usable local PTY and permission to create a Unix socket; restricted execution sandboxes may block it. Never run tests as a privileged account to work around deployment permissions. The control test additionally uses Linux /proc, boot-time clocks, parent-death signals, interactive PTYs and real command execution inside an isolated temporary shell. They do not validate remote SSH policy or desktop action support.

The routing test uses mocked GUI/native notification calls and local forced-receiver subprocesses instead of real SSH. It must never send a message, open a GUI or use account credentials.

Optional installed-runtime visual tests are documented in INLINE_UI.md. The headless check uses synthetic messages and an isolated home. The Wayland check briefly displays a synthetic card; never run it on someone else’s desktop without their permission. Do not replace those fixtures with real inbox data or publish screenshots of private requests.

Add meaningful tests for changed security boundaries. Record multi-PC acceptance separately and truthfully. Do not describe a syntax check as end-to-end verification. Use Python’s standard library unless a dependency has a clear reviewed purpose. Never evaluate peer messages or SSH_ORIGINAL_COMMAND.

## Before opening a pull request

- Run relevant checks and describe what was actually verified.
- Inspect the staged diff for private paths, identities, addresses, credentials, logs, screenshots and personal information.
- Use generic peer IDs and synthetic placeholders in examples.
- Document compatibility changes, migration and removal behavior.
- Follow SECURITY.md for vulnerabilities instead of public disclosure.

Use your GitHub-provided no-reply commit email if you do not want your personal email in public history. Official Omarchy integration requires upstream review; project contributors must not imply endorsement.
