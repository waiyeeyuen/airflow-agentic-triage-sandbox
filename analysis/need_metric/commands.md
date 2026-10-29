# Need-metric collection commands

Collection target: every non-PR issue opened in `apache/airflow` from
`2026-07-01T00:00:00Z` through `2026-09-30T23:59:59Z`. Data must be collected
through read-only GitHub API requests; do not run any GitHub mutation command.

The script invokes these commands (PowerShell quoting shown):

```powershell
gh auth status
gh api repos/apache/airflow --jq '{full_name,default_branch,archived}'
gh api --paginate --slurp -X GET search/issues `
  -f 'q=repo:apache/airflow is:issue created:2026-07-01..2026-09-30' `
  -f sort=created -f order=asc -f per_page=100
gh api --paginate --slurp -X GET `
  repos/apache/airflow/issues/ISSUE_NUMBER/timeline `
  -H 'Accept: application/vnd.github+json' -f per_page=100
```

Reproduce from the assignment workspace after authenticating `gh`:

```powershell
$gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
if (-not $gh) {
  $gh = (Get-ChildItem '.tools/gh' -Recurse -Filter gh.exe |
    Select-Object -First 1 -ExpandProperty FullName)
}
& $gh auth status
& 'analysis/need_metric/collect_need_metric.ps1' -GhPath $gh
```

Use `-ReuseRaw` to resume without re-fetching timeline files already saved:

```powershell
& 'analysis/need_metric/collect_need_metric.ps1' -GhPath $gh -ReuseRaw
```

Raw search pages are saved as `raw/population_pages.json`. Each issue timeline is
saved immediately as `raw/timelines/<number>.json`, so an interrupted run resumes
without discarding completed requests. `issue_metrics.partial.json` is rewritten
after every analysed issue. The script rejects a Search API result at or above the
1,000-result cap and rejects any collected population count that differs from
`total_count`.

Collection completed at `2026-10-29T14:51:36Z` with the checksum-verified portable
GitHub CLI 2.103.2, authenticated as `waiyeeyuen`. The script collected 477 search
results and 477 timeline files. The authentication check and all API calls were
read-only; no GitHub mutation command was run.

The later Kaplan–Meier revision used `-ReuseRaw`, read the original collection
timestamp from `metadata.json`, and made no API request. This preserves the censoring
time for the 99 issues without an observed signal.
