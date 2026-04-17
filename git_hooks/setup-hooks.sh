#!/usr/bin/env bash
# Install git hooks from the repository into .git/hooks/ via symlinks.
# Run this once after cloning the repository.
#
# Usage: bash git_hooks/setup-hooks.sh

set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
project_root="$(dirname "$script_dir")"
git_hooks_dir="$project_root/.git/hooks"
hooks_src="$script_dir"

hooks_to_install=(
    pre-commit
    commit-msg
)

for hook in "${hooks_to_install[@]}"; do
    src="$hooks_src/$hook"
    dest="$git_hooks_dir/$hook"

    if [ ! -f "$src" ]; then
        echo "warning: source hook not found, skipping: $src" >&2
        continue
    fi

    # Make the source hook executable
    chmod +x "$src"

    # Remove existing hook (symlink or regular file)
    if [ -L "$dest" ]; then
        existing_target=$(readlink "$dest")
        echo "updating symlink: $dest -> $existing_target"
        rm "$dest"
    elif [ -f "$dest" ]; then
        echo "replacing existing hook: $dest"
        rm "$dest"
    fi

    # Create relative symlink
    ln -s "$src" "$dest"
    echo "installed: $hook -> $src"
done

echo "done. git hooks installed."