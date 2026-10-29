# Need-metric verification

Verified on 2026-10-29 UTC from the saved files, independently of the summary-writing
step in `collect_need_metric.ps1`.

## Population and filters

- Search API `total_count`: 477; saved search items: 477; unique issue records: 477;
  timeline files: 477.
- `raw/issue_author_bot_check.csv` has 477 rows and records login, GitHub account type,
  login-pattern match, and exclusion decision for every issue. The exact `type == Bot`
  list is the valid empty JSON array `raw/bot_type_issue_authors.json`; there were no
  Bot-type or login-pattern exclusions.
- Bot/account filtering is at script lines 37–46 and 146–162. A signal actor must be
  present, non-bot, and different from the issue author (lines 43–46). That predicate is
  applied before event classification (lines 78–103), so author activity and labels
  applied by templates, null actors, or bots cannot become signals.

## Independent statistics

A separate PowerShell calculation parsed `issue_metrics.json`; grouped the 477
`km_time_hours` values; maintained its own at-risk count; applied
`S(t) = S(t-) * (1 - d/n)` at each event time; and removed events plus censors after
each time. It did not call `Get-KaplanMeier` from the collection script.

- Whole-population KM: n=477, 378 events, 99 right-censored at the saved collection
  timestamp (record construction: lines 182–199; KM implementation: lines 231–275).
- KM Q1 4.85 h, median 54.88 h, Q3 1178.73 h. Qp is the earliest event time where
  cumulative incidence `1-S(t)` reaches p (p=.25, .50, .75). All three were reached.
- `S(48 h)=0.524109` and `S(168 h)=0.396226`; because the earliest censor was at
  773.7167 h, these equal 250/477 and 189/477. The KM median is therefore correctly
  between 48 and 168 h.
- Observed-signal subset only: n=378; R-7 median 18.12 h; IQR 2.31–146.65 h;
  range 0.06–2534.09 h.
- Full population: n=477; no signal by collection 99/477 (20.8%). Outcome partition:
  204 open + 273 closed + 0 observed converted-to-Discussion = 477.

## SHA-256

```text
1fc7bb1a59fd11d5ca85a71b1e84f7cc7f57747e6c8dc82862b258385640bc91  raw/population_pages.json
3e453eef8a9abc49aed3e0081c7bca2a5dd2ebb612cff50e9ebb629468d6df1d  issue_metrics.json
7f806eba3b08793759bb826c1cf39095b0af71c526e1e756fa3353e216d3714c  summary.json
ead74e4a0d732b3d28e22fce4cccc23ed2ea6e0039fda1966de0e64a222e642a  km_summary.json
a967f18091df5e44262d10fc69630404e8c8c5df98f0d5dad913d3b2b896eec8  km_curve.json
37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570  raw/bot_type_issue_authors.json
9a8ea1700a6144fb5a593ba7faa21b4fafb241652a16eb4745d7aa7978b77fa9  raw/issue_author_bot_check.csv
```

Limitations include invisible Slack/mailing-list triage, edited issue bodies, actor-type
misclassification, and population undercount: issues converted to Discussions can leave
Issues search, while deleted spam is absent entirely. Thus zero observed conversions is
not evidence that no issue from the window was converted.
