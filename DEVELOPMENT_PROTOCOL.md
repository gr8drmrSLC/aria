# DEVELOPMENT_PROTOCOL.md — ARIA

The 8-step regression safety protocol for every change to working code.

AI tools are fast. Fast changes that break things silently are the most
common failure mode in AI-assisted development. This protocol exists to
make regressions catch themselves.

---

## The 8-step protocol

Before making any change to existing, working code:

**1. State what is currently working and must not break.**

Run the smoke test. Record its output. That output is your baseline.

```bash
python tests/smoke_test.py
# Expected: 16/16 checks passed
```

**2. Identify the smallest change that achieves the goal.**

Ask: can I accomplish this by changing one function, one file, one constant?
If the answer is no, ask why. Most changes that seem to require touching
many files can be decomposed into smaller, independently verifiable steps.

**3. Check whether the change affects any other file or system.**

```bash
grep -r "function_or_constant_you_are_changing" core/ dashboard/ runner.py
```

ARIA's module dependency map:
```
runner.py → core.ingest, core.store, core.analyst, core.decider, core.reporter
dashboard/app.py → core.store
core.reporter → core.analyst (_charge, _guard)
core.analyst → core.budget_guard
core.config → loaded by new modules
```

**4. Make the change.**

One logical change per session step. Do not bundle unrelated edits.

**5. Verify the change works.**

Run the smoke test again. If the change was to a specific trigger or module,
also test it directly with synthetic data in a Python shell.

```bash
python tests/smoke_test.py
python -c "from core.decider import decide; print(decide([{'novelty_score': 9.0, 'categories': ['cs.AI']}]*5, []))"
```

**6. Verify nothing that was working before is now broken.**

Diff the smoke test output against step 1. Every passing check must still pass.

**7. Commit with a message that explains *why*, not just *what*.**

```bash
# Wrong
git commit -m "update threshold"

# Right
git commit -m "feat: lower novelty_burst threshold from 30% to 20% — too few reports during low-activity periods"
```

**8. Update PROJECT_STATUS.md if the change was significant.**

A significant change is one that: changes the pipeline behavior, adds or
removes a module, changes deployment configuration, or introduces a new
dependency.

---

## ARIA-specific examples

### Changing a decider threshold

1. Run smoke test — verify trigger tests pass
2. Change constant in `core/decider.py` (or `.env`)
3. Check: `grep -r "NOVELTY_BURST_PCT\|VOLUME_SPIKE" core/`
4. Make change
5. Run `python -c "from core.decider import _trigger_novelty_burst; ..."` with synthetic data
6. Run full smoke test — all 16 checks must pass
7. Commit: "tuning: lower NOVELTY_BURST_PCT threshold — saw X missed reports"
8. Update PROJECT_STATUS.md if this affects baseline behavior

### Adding a new Claude API call

1. Identify current session spend path: `_guard.record()` in analyst.py and reporter.py
2. New call is the smallest addition — one function, wired to `_guard`
3. Check: `grep -r "_guard\|_charge" core/` — confirm both callers
4. Add function with `_guard.record()` immediately after `client.messages.create()`
5. Test with mock usage: `_guard.record("claude-sonnet-4-6", 100, 50)` — confirm no exception
6. Run smoke test — BudgetExceeded check must still pass
7. Commit: "feat: add X — calls Claude once per run, ~$Y/call"
8. Update BUDGET_POLICY.md daily spend estimate

### Changing the database schema

1. Run smoke test — confirm database CRUD check passes
2. Smallest change: one new column with a default, or one new table
3. Check: all callers of affected table (store.py, dashboard/app.py, runner.py)
4. Write migration SQL. Test on a copy of the database first.
5. Apply migration: `sqlite3 data/aria.db < migration.sql`
6. Run smoke test — database checks must still pass
7. Commit: "feat: add X column to papers table — needed for Y"
8. Update DECISIONS.md if this was a non-obvious design decision

---

## What counts as a protocol violation

- Making two unrelated changes in the same step
- Running the smoke test only at the end, not at the start
- Committing without checking that previously passing tests still pass
- Changing working code without reading which other modules depend on it
- Suppressing a `BudgetExceeded` exception instead of halting

---

## Running the smoke test

```bash
# From the aria/ root with venv active
python tests/smoke_test.py

# On EC2
ssh -i ~/.ssh/investor-key.pem ubuntu@3.139.164.142 \
  "cd ~/aria && source .venv/bin/activate && python tests/smoke_test.py"
```

Expected output when all checks pass:
```
  PASS  core.analyst imports
  PASS  core.ingest imports
  PASS  core.decider imports
  PASS  core.store imports
  PASS  core.reporter imports
  PASS  core.config loads
  PASS  SESSION_SPEND_LIMIT_USD set
  PASS  BudgetExceeded raised when over limit
  PASS  budget guard tracks spend and call count
  PASS  identify_cross_domain filters correctly
  PASS  decider novelty_burst trigger fires
  PASS  decider cross_domain trigger fires
  PASS  decider returns should_report key
  PASS  _select_notable_papers returns top 10
  PASS  database init and CRUD
  PASS  reporter fallback report generates
  PASS  .gitignore covers secrets

17/17 checks passed
```
