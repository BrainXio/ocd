#!/usr/bin/env bash
# Configure git to use .githooks/ as the hooks directory.
# Run this once after cloning the repository.
#
# Usage: bash .githooks/setup-hooks.sh

set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"

hooks_to_make_executable=(
    pre-commit
    pre-push
    commit-msg
)

for hook in "${hooks_to_make_executable[@]}"; do
    src="$script_dir/$hook"
    if [ -f "$src" ]; then
        chmod +x "$src"
        echo "executable: $hook"
    else
        echo "warning: hook not found, skipping: $src" >&2
    fi
done

# Set core.hooksPath to use .githooks/ instead of .git/hooks/
git config core.hooksPath .githooks/
echo "configured: core.hooksPath = .githooks/"
echo "done. git hooks installed."