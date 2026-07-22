<!-- last_verified: 2026-07-22 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance view of the enhancement pipeline — how much audio has been
super-resolved and, above all, the **storage-amplification** story (original →
enhanced bytes) that the sample exists to demonstrate.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /jobs/stats`, `GET /jobs/stats/activity`, `GET /jobs`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — 4 stat cards
- `apps/web/src/components/dashboard/enhancement-chart.tsx` — enhanced-output bytes/day bar chart
- `apps/web/src/components/dashboard/recent-enhancements-table.tsx` — latest jobs
- `apps/web/src/lib/queries.ts` — `useEnhancementStats()`, `useEnhancementActivity()`, `useJobs()`
- `services/api/app/service/jobs.py` — `get_enhancement_stats()`, `get_enhancement_activity()`

## Canonical Files
- Dashboard stat cards: `apps/web/src/components/dashboard/stats-cards.tsx`
- Stats service logic: `services/api/app/service/jobs.py`

## Inputs
- None (dashboard loads data automatically; stats poll every 5s)

## Outputs
- `GET /jobs/stats` → `EnhancementStats` (files_enhanced, jobs_total, total_original/enhanced bytes + human, amplification_ratio, avg_input/output_sample_rate, jobs_by_status)
- `GET /jobs/stats/activity?days=7` → `EnhancementActivityPoint[]` (enhanced-output bytes per day)
- `GET /jobs` → `EnhancementJob[]` for the recent-enhancements table

## Flow
- Page loads → stats, activity, and recent jobs fetched in parallel
- Stat cards: **Files enhanced**, **Storage amplification** (enhanced ÷ original bytes — the marquee metric, with the byte totals as a sub-line), **Avg bandwidth gain** (input → output sample rate), **Jobs by status**
- Chart: enhanced-output volume per day (bytes, last 7 days)
- Table: recent enhancements (input, sample-rate in→out, amplification, status)

## Edge Cases
- API unavailable → inline error states with retry
- No enhancements yet → empty chart/table messages; amplification shows "—"
- Large job count → stats iterate all job manifests (fine for a single-tenant demo)

## UX States
- Loading: skeletons for cards, chart, table
- Empty: "No enhancements yet" messaging
- Loaded: populated cards, chart, table (status badges update live via polling)

## Verification
- Test files: `services/api/tests/test_jobs.py` (`test_enhancement_stats_aggregate`)
- Required cases: stats with a completed job, empty state, API error fallback
- Quick verify command: `pnpm test:api`
- Pass criteria: aggregation correct; tests green; no ruff violations

## Related Docs
- [Enhancement Jobs](enhancement-jobs.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
