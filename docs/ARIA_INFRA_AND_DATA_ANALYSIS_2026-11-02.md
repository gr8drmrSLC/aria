# ARIA infrastructure, data and posting review — 2026-11-02

Status: analysis and discussion only. **Nothing here has been acted on.** Read-only checks were
made against the live site and the EC2 host. No personal details are included (public repo).

## 1. Live check (2026-11-02)

- Dashboard: HTTP 200 in 0.4 s; http redirects to https.
- GitHub Pages: HTTP 200. The export action succeeded on 10/27–10/30 and 11/2.
- TLS: Let's Encrypt, expires 2027-01-04. Auto-renewal was **not** verified.
- EC2: `aria-runner` and `aria-dashboard` active; host up about 8 weeks. Last pipeline run
  2026-10-30 produced report 87. Next run Tue 2026-11-03 07:00 UTC.
- "0 papers in last 24h" on a Monday is expected (pipeline runs Tue–Fri).

## 2. What ARIA occupies on EC2

| Item | Size | Notes |
|---|---|---|
| `.venv` | 181 MB | Rebuildable; not an archive candidate |
| `data/aria.db` | 37 MB | Grows about 5 MB/month (about 60 MB/year) |
| `.git` | 18 MB | Only needed for deploys |
| Logs, code, docs | about 3 MB | Negligible |
| **Total** | **238 MB** | Disk is 29 GB with 13 GB free |

Space on the same host that is **not** ARIA's: a 3.5 GB db_backups folder, 3.6 GB of Docker data
(579 MB reclaimable), a 624 MB backups folder and 883 MB of `/var/log`. These were not inspected.
Memory, not disk, is the tighter constraint: another project's orchestrator uses about 1.4 GB,
ARIA's two services about 130 MB combined (see ADR-014).

**Conclusion (owner, 2026-11-02): the memory/space savings from moving ARIA are negligible, so a
move is not important now.** Deferred, not rejected.

## 3. Can the data answer "what has ARIA seen over six months?"

Mostly yes. The server database holds 16,064 papers (3/31–10/30; abstracts, authors, categories,
novelty scores and free-text themes; 15,100 scored), 87 reports, 347 baseline rows over 4
categories, and 90 ingest days. A weekly S3 backup exists (not verified in this review).

Caveats:
- **Not retrievable from outside.** `/api/reports` returns only the newest 20 and `/api/papers`
  only 24 hours. History exists only inside the EC2 database and its backups.
- **Sampling, inferred.** Runs ingest exactly 200 papers (logged on 10/30; monthly counts are
  multiples of 200). Raw volume trends are therefore artifacts; mix and novelty trends are meaningful.
  The ingest code was not read to confirm this.
- **Gaps.** About 964 papers are unscored. August has 1,003 papers versus about 2,600–3,000 in other
  months; the cause is undiagnosed.
- **Score drift.** Novelty is model-assigned, so changes across months may reflect model or prompt
  changes. Themes are free text and not normalized.

First-pass analysis, once approved: read-only copy of the database to the laptop; theme emergence by
month, category mix, trigger rates, novelty over time.

## 4. Hosting and Cloudflare options

A `duckdns.org` name cannot be proxied by Cloudflare (DNS is not owned). Real alternatives:
1. Stay as is (DuckDNS + nginx + Let's Encrypt): works, free, free-subdomain credibility.
2. Owned domain on Cloudflare proxying to the same EC2 box: hidden origin IP, caching, clean URL.
3. Cloudflare Tunnel: as 2, with ports 80/443 closed and nginx retired. No meaningful disk/RAM change.
4. Static-only on Cloudflare Pages: stop the Flask service (about 66 MB RAM) and nginx; the live JSON
   API goes away and the poster would read static files.
5. Take ARIA off EC2 entirely (scheduled job on GitHub Actions, database in Cloudflare R2, static
   Pages site): zero EC2 footprint, but a real refactor.

Footprint-reduction options (if ever wanted):
- Tiered archive: monthly export of papers older than about 90 days to compressed files; strip abstract
  text from live rows, keeping id, categories, score and themes. **Structural** if delete-after-verify
  (checksum) is enforced in code; **soft** if it depends on remembering to run it.
- Laptop pull job (`rsync`/`scp` when connected) as one copy, with S3 as the second; a laptop that is
  sometimes off must not be the only archive.

Recommended order if revisited: trend analysis first, then the archive job, then decide Tunnel versus
static-only. Another repo's production-hosting gate concerns client OAuth and Meta review and does not
block an ARIA DNS change. ARIA is a portfolio project, so a domain shared with a business brand would
link the two; choose deliberately. Cloudflare account state was not inspected.

## 5. Post repetition

Every post embeds the same intro paragraph and swaps only a few numbers. Options:
1. Rotate several templates (easy, still templated).
2. Lead with the specific finding from the report; use the intro about once a month. **Structural.**
3. Generate each post with Claude through the budget guard, store post text, and reject any post too
   similar to the last 10. **Structural.** Optionally require a one-line human approval.

Suggested: 2 and 3 together. Reach was low (median about 180 impressions), so weekly posts built on a
six-month trend analysis may outperform daily ones. Related: ADR-015 and
`docs/LINKEDIN_POSTING_FOLLOWUP_2026-11-02.md`.

## 6. Open decisions

- Whether to run the trend analysis (read-only database copy) and the post redesign first.
- Read-only breakdown of the backups and Docker volumes on the host (not ARIA's, not yet inspected).
- Domain and live-API choices are moot while the move is deferred.
