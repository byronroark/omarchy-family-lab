#!/usr/bin/env bash
# Read-only inventory; run separately on each relevant account/PC.
set -u
for name in python3 ssh ssh-keygen tmux omarchy-notification-send omarchy-launch-terminal; do
  command -v "$name" || true
done
id
uname -r
tmux -V
ssh -V
command -v omarchy >/dev/null && omarchy version
command -v hyprctl >/dev/null && hyprctl version
command -v hyprctl >/dev/null && hyprctl monitors all
command -v nvidia-smi >/dev/null && nvidia-smi
printf '\nInspect local Omarchy command help and packaged helper source before installing.\n'
