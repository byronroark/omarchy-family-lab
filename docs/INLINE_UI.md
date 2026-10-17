# Themed inline request cards

The repository now includes an **experimental Omarchy shell plugin**, `community.family-lab`, alongside the CLI. It is not an official Omarchy plugin or endorsed distribution. The root manifest follows the installed Omarchy plugin schema; initial runtime checks used Omarchy **4.0.4-1** and Quickshell **0.3.1**. Other releases need their own compatibility checks.

## Interface

A compact, monospace card shows the learner, request text, relay provenance where relevant, the number of waiting requests and expiry progress. The buttons are directly in the card:

```text
[ family lab ]                         2 waiting
> learner-a
Could you help explain this command?

[ Open terminal ] [ Ask Mom ] [ Dismiss ]
view only · control needs local approval
```

Ask Mom appears only when an enrolled forwarding route is valid for that learner and original request. Relayed/already-forwarded requests cannot loop through another helper. Open terminal is read-only. There is deliberately no approve-control, sudo, arbitrary-command or automatic AI action in this interface. Local learner control approval remains in CONTROL.md.

Only the oldest live request is shown at a time, with the waiting count. Successful open, forward or dismiss advances to the next. A failed action keeps the request available and shows a brief retry message. The card can be operated with a mouse or keyboard focus/Tab/Enter after interaction. It never asks for exclusive keyboard focus. Long messages scroll, button labels fit the available width, and the full card can scroll at unusually large font sizes.

The popup appears at the bottom right of the first screen, away from the normal top-right notification stack. It respects the scalar bar position/size supplied by the host. No monitor layout or desktop shortcuts are changed. It uses a normal top layer, not an above-lock-screen surface.

## Theme integration

The card imports the installed shell's `qs.Commons` and `qs.Ui`, rather than copying a theme or patching packaged files:

- `Color.notifications`, `Color.accent`, `Color.muted` and `Color.urgent` supply palette roles.
- `Style.font` and the host's scalar bar font use Omarchy's monospace font selection and text scale.
- Shared `Ui.Button`, `Border`, spacing, corner radius and control state tokens provide hover, keyboard focus, pressed and disabled states.

These are bindings to the live shell singletons, so normal Omarchy theme/text changes flow through the interface. The plugin has no separate theme and does not edit `/usr/share/omarchy`, user theme files, terminal configuration or Hyprland settings. Request text uses `Text.PlainText` throughout; markup, links and command-looking strings are not executable.

## Install and enable in stages

First complete INSTALL.md, ROUTING.md and any desired CONTROL.md enrollment. Update/review the installed CLI on the helper PC. The shell plugin installer does **not** run the CLI installer or enroll keys for you.

Keep `family-lab watch` running in a visible graphical terminal as the fallback dispatcher. The default CLI configuration remains `"notification_backend": "native"`.

After reviewing the source and the installed `omarchy plugin` help, add the repository through Omarchy's plugin manager:

```sh
omarchy plugin add https://github.com/byronroark/omarchy-family-lab.git
```

The installed Omarchy workflow clones plugins disabled for review. Inspect the checkout, root manifest and `plugin/` sources. Then enable deliberately:

```sh
omarchy plugin enable community.family-lab
```

The plugin expects the reviewed CLI at `~/.local/bin/family-lab`. It does not search for a private key or make direct SSH calls. In the helper's local `~/.config/family-lab/config.json`, set:

```json
"notification_backend": "inline"
```

This is a fragment inside the existing config; preserve your routes and other fields. Only change the helper endpoint being tested. The plugin polls local state about every two seconds. With no requests it creates no popup. Do not install a second notification daemon or replace/clone the built-in notification service for this feature.

## DND and fallback

The local CLI reads the installed desktop's `omarchy-shell notifications dndState` IPC method. DND hides inline request cards without discarding them; unexpired requests become available when DND ends. If DND state cannot be read, the inline path hides request content and does not renew its health heartbeat. The ordinary native notification path handles fallback according to the desktop's own notification policy.

The frontend writes a private heartbeat only after valid state and successful popup loading (or when no popup is needed). Reading UI-state JSON alone does not renew it. If it is absent or more than six seconds old, the visible `family-lab watch` dispatcher restores unhandled requests to the native notification/menu path. Disabling the plugin or changing backend to `native` also allows recovery. Already dismissed or successfully native-delivered requests are not shown again as inline cards. Keep the watcher running: without it there is no automatic native fallback. A heartbeat confirms polling, not that a human saw the card.

Disabling the plugin or DND does not end an existing terminal control connection. Use the learner revoke shortcut or stop command for that. Request expiry still applies to every action. Dialog fallback continues to work on installations that do not support the plugin API.

## Compatibility and tests

Automated Python tests cover the UI-state/action schema, DND and unknown DND, heartbeat recovery, native-delivery deduplication, failed-action retry, dismissal and exclusion of control/admin actions. A dependency-free Node test checks the QML JavaScript model's fixed argument vectors and rejected action kinds/targets. Node is a development test dependency only.

On an installed Omarchy development machine:

```sh
python3 tests/check_inline_qml.py
```

This launches an isolated **offscreen** Quickshell configuration with a temporary home and the real installed theme/UI components. It renders synthetic light/dark cards and checks action dispatch, busy/expired guards, keyboard focus, scaling, long-message bounds and service loading without a popup. It neither installs the plugin nor contacts another PC. Set `FAMILY_LAB_PREVIEW_DIR` to an output directory if synthetic preview PNGs are desired.

The separate optional live check:

```sh
python3 tests/check_inline_wayland.py
```

briefly displays **one synthetic popup** in an isolated Quickshell instance on the current Wayland desktop, then closes it automatically. Its CLI is a temporary stub; no action can contact another PC. This validates real layer-shell popup loading. Initial local checks passed on the versions above. CI does not have an Omarchy Wayland desktop and does not run either optional visual test.

Before regular use, validate installation/host injection, actual live theme/font switching, DND on/off, screen/bar placement, keyboard interaction, long messages, forwarding over real SSH, helper offline/retry, expiry and plugin disable/crash fallback. Synthetic rendering and popup smoke tests do not replace these deployment gates.

## Disable, update and remove

Set local backend to `native` and keep the watcher running; inspect unhandled requests with `family-lab inbox`. Disable with the installed plugin manager's `omarchy plugin disable community.family-lab`. Remove through that manager only after confirming fallback. Removing the plugin does not remove CLI scripts, keys, routes or learner consent state.

The service deliberately does not set `keepLoaded`, so development hot reload can replace it. Request state remains in the private CLI inbox across UI reloads. Inspect updates with the installed plugin manager and rerun the relevant compatibility checks. The root manifest and shared UI APIs can change between Omarchy releases; do not assume universal compatibility.
