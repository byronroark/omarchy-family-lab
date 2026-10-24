#!/usr/bin/env bash
# Local, reviewable setup: plan by default; no downloads or curl-to-shell.
set -euo pipefail
family_source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ ${1:-} == features ]]; then
  shift
  exec /usr/bin/python3 -I "$family_source_dir/setup/features_setup.py" "$@"
fi
exec /usr/bin/python3 -I "$family_source_dir/setup/family_install.py" "$@"
