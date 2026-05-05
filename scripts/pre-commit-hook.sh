#!/bin/bash
# ARIA pre-commit hook — ruff lint + CHANGELOG auto-generation
#
# Install: cp scripts/pre-commit-hook.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
# Uninstall: rm .git/hooks/pre-commit

set -euo pipefail

# ── Ruff lint: auto-fix then verify ──────────────────────────────────────────
if command -v ruff &>/dev/null; then
    RUFF=ruff
else
    RUFF=.venv/bin/ruff
fi

DIRS="core/ dashboard/"

echo "Running ruff auto-fix..."
$RUFF check $DIRS --fix --quiet 2>/dev/null || true

# Re-stage any files ruff modified
git diff --name-only | grep '\.py$' | xargs -r git add

# Final check — block only if unfixable errors remain
if ! $RUFF check $DIRS --quiet 2>/dev/null; then
    echo ""
    echo "Linting failed — some errors require manual fixes. See above."
    exit 1
fi
echo "Linting passed."

# ── CHANGELOG auto-update ────────────────────────────────────────────────────
STAGED_PY=$(git diff --cached --name-only | grep '\.py$' || true)
STAGED_CHANGELOG=$(git diff --cached --name-only | grep 'CHANGELOG.md' || true)

if [ -n "$STAGED_PY" ] && [ -z "$STAGED_CHANGELOG" ]; then
    echo ""
    echo "Auto-generating CHANGELOG entry..."

    CHANGELOG_SCRIPT="$HOME/shared/changelog_ai.py"
    if [ -f "$CHANGELOG_SCRIPT" ]; then
        export CHANGELOG_PROJECT="ARIA — Autonomous Research Intelligence Agent"
        AI_ENTRY=$(git diff --cached | python "$CHANGELOG_SCRIPT" 2>/dev/null || true)

        if [ -n "$AI_ENTRY" ]; then
            DATE=$(date +%Y-%m-%d)
            TEMP=$(mktemp)
            echo -e "## [$DATE]\n\n$AI_ENTRY\n" > "$TEMP"
            cat CHANGELOG.md >> "$TEMP"
            mv "$TEMP" CHANGELOG.md
            git add CHANGELOG.md
            echo "CHANGELOG.md updated — review the entry after committing."
        fi
    else
        echo "changelog_ai.py not found at $CHANGELOG_SCRIPT — skipping auto-generation."
    fi
fi

echo "Pre-commit checks passed."
