[CmdletBinding()]
param(
    [string]$Repository = "apache/airflow",
    [datetime]$WindowStartUtc = [datetime]::Parse("2026-07-01T00:00:00Z").ToUniversalTime(),
    [datetime]$WindowEndUtc = [datetime]::Parse("2026-09-30T23:59:59Z").ToUniversalTime(),
    [string]$SnapshotSha = "270b2abfc258c512a0b931af425904321360d043",
    [string]$GhPath = "gh",
    [string]$OutputDirectory = $PSScriptRoot,
    [string]$CollectionTimestampUtc = "",
    [switch]$ReuseRaw
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Invoke-GhJson {
    param([Parameter(Mandatory)][string[]]$Arguments)
    $text = & $GhPath @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "gh failed ($LASTEXITCODE): gh $($Arguments -join ' ')`n$($text -join "`n")"
    }
    return ($text -join "`n")
}

function Write-Utf8Json {
    param([Parameter(Mandatory)]$Value, [Parameter(Mandatory)][string]$Path, [int]$Depth = 100)
    $json = ConvertTo-Json -InputObject $Value -Depth $Depth
    [System.IO.File]::WriteAllText($Path, $json + "`n", [System.Text.UTF8Encoding]::new($false))
}

function ConvertFrom-PagedJson {
    param([Parameter(Mandatory)][string]$Json)
    $pages = @($Json | ConvertFrom-Json -Depth 100)
    return ,$pages
}

function Test-BotLogin {
    param($User)
    if ($null -eq $User) { return $false }
    return ($User.type -eq "Bot" -or $User.login -match '(?i)(\[bot\]|-bot$|^bot-)')
}

function Test-HumanNonAuthor {
    param($Actor, [string]$AuthorLogin)
    if ($null -eq $Actor -or [string]::IsNullOrWhiteSpace($Actor.login)) { return $false }
    return (-not (Test-BotLogin $Actor)) -and ($Actor.login -ne $AuthorLogin)
}

function Get-PercentileType7 {
    param([double[]]$SortedValues, [double]$Probability)
    if ($SortedValues.Count -eq 0) { return $null }
    if ($SortedValues.Count -eq 1) { return $SortedValues[0] }
    $h = ($SortedValues.Count - 1) * $Probability
    $lower = [math]::Floor($h)
    $upper = [math]::Ceiling($h)
    if ($lower -eq $upper) { return $SortedValues[$lower] }
    return $SortedValues[$lower] + (($h - $lower) * ($SortedValues[$upper] - $SortedValues[$lower]))
}

function Get-SignalActor {
    param($Event)
    if ($null -ne $Event.actor) { return $Event.actor }
    if ($null -ne $Event.user) { return $Event.user }
    return $null
}

function Convert-ToUtcDateTime {
    param([Parameter(Mandatory)]$Value)
    if ($Value -is [datetime]) { return $Value.ToUniversalTime() }
    if ($Value -is [datetimeoffset]) { return $Value.UtcDateTime }
    return [datetimeoffset]::Parse(
        [string]$Value,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::AssumeUniversal
    ).UtcDateTime
}

function Get-FirstTriageSignal {
    param([object[]]$Events, [string]$AuthorLogin)
    $candidateEvents = foreach ($event in $Events) {
        if ($null -eq $event.created_at) { continue }
        $actor = Get-SignalActor $event
        if (-not (Test-HumanNonAuthor $actor $AuthorLogin)) { continue }
        $kind = $null
        switch ($event.event) {
            "commented" { $kind = "comment" }
            "labeled" { $kind = "label_added" }
            "unlabeled" {
                if ($event.label.name -eq "needs-triage") { $kind = "needs-triage_removed" }
                else { $kind = "label_removed" }
            }
            "closed" { $kind = "closed" }
            "converted_to_discussion" { $kind = "converted_to_discussion" }
        }
        if ($null -ne $kind) {
            [pscustomobject]@{
                created_at = Convert-ToUtcDateTime $event.created_at
                kind = $kind
                actor = $actor.login
            }
        }
    }
    return $candidateEvents | Sort-Object created_at | Select-Object -First 1
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$rawDirectory = Join-Path $OutputDirectory "raw"
$timelineDirectory = Join-Path $rawDirectory "timelines"
New-Item -ItemType Directory -Force -Path $rawDirectory, $timelineDirectory | Out-Null

$metadataPath = Join-Path $OutputDirectory "metadata.json"
$collectionAsOfUtc = if (-not [string]::IsNullOrWhiteSpace($CollectionTimestampUtc)) {
    Convert-ToUtcDateTime $CollectionTimestampUtc
} elseif ($ReuseRaw -and (Test-Path -LiteralPath $metadataPath)) {
    $oldMetadata = [System.IO.File]::ReadAllText($metadataPath) | ConvertFrom-Json
    Convert-ToUtcDateTime $oldMetadata.collected_at_utc
} else {
    [datetime]::UtcNow
}

$collectionStartedUtc = [datetime]::UtcNow
$startDate = $WindowStartUtc.ToString("yyyy-MM-dd")
$endDate = $WindowEndUtc.ToString("yyyy-MM-dd")
$query = "repo:$Repository is:issue created:$startDate..$endDate"
$populationPagesPath = Join-Path $rawDirectory "population_pages.json"

if (-not $ReuseRaw -or -not (Test-Path -LiteralPath $populationPagesPath)) {
    $populationJson = Invoke-GhJson @(
        "api", "--paginate", "--slurp", "-X", "GET", "search/issues",
        "-f", "q=$query", "-f", "sort=created", "-f", "order=asc", "-f", "per_page=100"
    )
    [System.IO.File]::WriteAllText($populationPagesPath, $populationJson + "`n", [System.Text.UTF8Encoding]::new($false))
}

$populationPages = ConvertFrom-PagedJson ([System.IO.File]::ReadAllText($populationPagesPath))
$reportedTotal = [int]$populationPages[0].total_count
if ($reportedTotal -ge 1000) {
    throw "GitHub Search API reports $reportedTotal issues; its 1,000-result cap prevents a complete population. Split the window before continuing."
}
$allItems = @($populationPages | ForEach-Object { $_.items })
$uniqueItems = @($allItems | Sort-Object number -Unique)
if ($uniqueItems.Count -ne $reportedTotal) {
    throw "Incomplete population: collected $($uniqueItems.Count) unique issues but Search API reported $reportedTotal."
}

$botIssues = @($uniqueItems | Where-Object { Test-BotLogin $_.user })
$humanIssues = @($uniqueItems | Where-Object { -not (Test-BotLogin $_.user) })
$authorChecks = @($uniqueItems | ForEach-Object {
    [pscustomobject]@{
        issue_number = [int]$_.number
        author_login = $_.user.login
        account_type = $_.user.type
        login_pattern_matches_bot = [bool]($_.user.login -match '(?i)(\[bot\]|-bot$|^bot-)')
        excluded_as_bot = [bool](Test-BotLogin $_.user)
    }
})
$botTypeAuthors = @($uniqueItems | Where-Object { $_.user.type -eq "Bot" } |
    ForEach-Object { [pscustomobject]@{ issue_number = [int]$_.number; author_login = $_.user.login; account_type = $_.user.type } })
Write-Utf8Json $botIssues (Join-Path $rawDirectory "excluded_bot_authored_issues.json")
Write-Utf8Json $humanIssues (Join-Path $rawDirectory "population_human_authored.json")
Write-Utf8Json $botTypeAuthors (Join-Path $rawDirectory "bot_type_issue_authors.json")
$authorChecks | Export-Csv -NoTypeInformation -Encoding utf8 (Join-Path $rawDirectory "issue_author_bot_check.csv")

$records = [System.Collections.Generic.List[object]]::new()
foreach ($issue in ($humanIssues | Sort-Object created_at, number)) {
    $timelinePath = Join-Path $timelineDirectory ("{0}.json" -f $issue.number)
    if (-not $ReuseRaw -or -not (Test-Path -LiteralPath $timelinePath)) {
        $timelineJson = Invoke-GhJson @(
            "api", "--paginate", "--slurp", "-X", "GET",
            "repos/$Repository/issues/$($issue.number)/timeline",
            "-H", "Accept: application/vnd.github+json", "-f", "per_page=100"
        )
        [System.IO.File]::WriteAllText($timelinePath, $timelineJson + "`n", [System.Text.UTF8Encoding]::new($false))
    }
    $timelinePages = ConvertFrom-PagedJson ([System.IO.File]::ReadAllText($timelinePath))
    $events = @($timelinePages | ForEach-Object { $_ })
    $createdUtc = Convert-ToUtcDateTime $issue.created_at
    $signal = Get-FirstTriageSignal $events $issue.user.login
    $convertedEvent = $events | Where-Object { $_.event -eq "converted_to_discussion" } | Sort-Object created_at | Select-Object -First 1
    $closedEvent = $events | Where-Object { $_.event -eq "closed" } | Sort-Object created_at | Select-Object -First 1
    $outcome = if ($null -ne $convertedEvent) { "converted_to_discussion" } elseif ($null -ne $closedEvent -or $issue.state -eq "closed") { "closed" } else { "open" }
    $delayHours = if ($null -ne $signal) { ($signal.created_at - $createdUtc).TotalHours } else { $null }
    $followupHours = if ($null -ne $delayHours) { $delayHours } else { ($collectionAsOfUtc - $createdUtc).TotalHours }
    if ($followupHours -lt 0) { throw "Negative follow-up for issue $($issue.number)." }
    $records.Add([pscustomobject]@{
        number = [int]$issue.number
        source_url = $issue.html_url
        author_login = $issue.user.login
        created_at = $createdUtc.ToString("o")
        outcome = $outcome
        first_signal_at = if ($null -ne $signal) { $signal.created_at.ToString("o") } else { $null }
        first_signal_kind = if ($null -ne $signal) { $signal.kind } else { $null }
        first_signal_actor = if ($null -ne $signal) { $signal.actor } else { $null }
        delay_hours = if ($null -ne $delayHours) { [math]::Round($delayHours, 4) } else { $null }
        km_time_hours = [math]::Round($followupHours, 4)
        km_event_observed = ($null -ne $signal)
        still_untriaged_after_2d = ($null -eq $delayHours -or $delayHours -gt 48)
        still_untriaged_after_7d = ($null -eq $delayHours -or $delayHours -gt 168)
        never_human_signal_as_of_collection = ($null -eq $signal)
        timeline_file = "raw/timelines/$($issue.number).json"
    })
    Write-Utf8Json $records (Join-Path $OutputDirectory "issue_metrics.partial.json")
}

$recordArray = @($records)
Write-Utf8Json $recordArray (Join-Path $OutputDirectory "issue_metrics.json")
$recordArray | Export-Csv -NoTypeInformation -Encoding utf8 (Join-Path $OutputDirectory "issue_metrics.csv")

function Get-GroupSummary {
    param([object[]]$Group, [string]$Name)
    $observed = @($Group | Where-Object { $null -ne $_.delay_hours } | ForEach-Object { [double]$_.delay_hours } | Sort-Object)
    $count = $Group.Count
    [pscustomobject]@{
        group = $Name
        n = $count
        n_observed_signal = $observed.Count
        median_hours_observed = if ($observed.Count) { [math]::Round((Get-PercentileType7 $observed 0.50), 2) } else { $null }
        q1_hours_observed = if ($observed.Count) { [math]::Round((Get-PercentileType7 $observed 0.25), 2) } else { $null }
        q3_hours_observed = if ($observed.Count) { [math]::Round((Get-PercentileType7 $observed 0.75), 2) } else { $null }
        min_hours_observed = if ($observed.Count) { [math]::Round($observed[0], 2) } else { $null }
        max_hours_observed = if ($observed.Count) { [math]::Round($observed[-1], 2) } else { $null }
        still_untriaged_after_2d_n = @($Group | Where-Object still_untriaged_after_2d).Count
        still_untriaged_after_2d_pct = if ($count) { [math]::Round(100 * @($Group | Where-Object still_untriaged_after_2d).Count / $count, 1) } else { $null }
        still_untriaged_after_7d_n = @($Group | Where-Object still_untriaged_after_7d).Count
        still_untriaged_after_7d_pct = if ($count) { [math]::Round(100 * @($Group | Where-Object still_untriaged_after_7d).Count / $count, 1) } else { $null }
        never_human_signal_n = @($Group | Where-Object never_human_signal_as_of_collection).Count
        never_human_signal_pct = if ($count) { [math]::Round(100 * @($Group | Where-Object never_human_signal_as_of_collection).Count / $count, 1) } else { $null }
    }
}

function Get-KaplanMeier {
    param([object[]]$Group)
    $observations = @($Group | ForEach-Object {
        [pscustomobject]@{ time = [double]$_.km_time_hours; event = [bool]$_.km_event_observed }
    } | Sort-Object time)
    $atRisk = $observations.Count
    $survival = 1.0
    $curve = [System.Collections.Generic.List[object]]::new()
    $q1 = $null
    $median = $null
    $q3 = $null
    foreach ($timeGroup in ($observations | Group-Object time | Sort-Object { [double]$_.Name })) {
        $time = [double]$timeGroup.Name
        $events = @($timeGroup.Group | Where-Object event).Count
        $censored = $timeGroup.Count - $events
        if ($events -gt 0) {
            $survival *= (1.0 - ($events / $atRisk))
        }
        $curve.Add([pscustomobject]@{
            time_hours = [math]::Round($time, 4)
            at_risk = $atRisk
            events = $events
            censored = $censored
            survival = [math]::Round($survival, 10)
        })
        if ($null -eq $q1 -and $survival -le 0.75) { $q1 = $time }
        if ($null -eq $median -and $survival -le 0.50) { $median = $time }
        if ($null -eq $q3 -and $survival -le 0.25) { $q3 = $time }
        $atRisk -= ($events + $censored)
    }
    $survivalAt48 = ($curve | Where-Object { $_.time_hours -le 48 } | Select-Object -Last 1).survival
    $survivalAt168 = ($curve | Where-Object { $_.time_hours -le 168 } | Select-Object -Last 1).survival
    return [pscustomobject]@{
        summary = [pscustomobject]@{
            n = $observations.Count
            events = @($observations | Where-Object event).Count
            right_censored = @($observations | Where-Object { -not $_.event }).Count
            q1_hours = if ($null -ne $q1) { [math]::Round($q1, 2) } else { $null }
            median_hours = if ($null -ne $median) { [math]::Round($median, 2) } else { $null }
            q3_hours = if ($null -ne $q3) { [math]::Round($q3, 2) } else { $null }
            q1_reached = ($null -ne $q1)
            median_reached = ($null -ne $median)
            q3_reached = ($null -ne $q3)
            survival_at_48h = [math]::Round([double]$survivalAt48, 6)
            survival_at_168h = [math]::Round([double]$survivalAt168, 6)
            quantile_definition = "Qp is the earliest event time where 1 - KM survival is at least p; Q1 p=0.25, median p=0.50, Q3 p=0.75. Censoring occurs at the collection timestamp."
        }
        curve = @($curve)
    }
}

$summaries = [System.Collections.Generic.List[object]]::new()
$summaries.Add((Get-GroupSummary $recordArray "all_human_authored_issues"))
foreach ($outcome in @("open", "closed", "converted_to_discussion")) {
    $summaries.Add((Get-GroupSummary @($recordArray | Where-Object outcome -eq $outcome) $outcome))
}

$km = Get-KaplanMeier $recordArray
Write-Utf8Json $km.summary (Join-Path $OutputDirectory "km_summary.json")
Write-Utf8Json $km.curve (Join-Path $OutputDirectory "km_curve.json")
$km.curve | Export-Csv -NoTypeInformation -Encoding utf8 (Join-Path $OutputDirectory "km_curve.csv")

$metadata = [pscustomobject]@{
    repository = $Repository
    window_start_utc = $WindowStartUtc.ToString("o")
    window_end_utc = $WindowEndUtc.ToString("o")
    collected_at_utc = $collectionAsOfUtc.ToString("o")
    analysis_recomputed_at_utc = [datetime]::UtcNow.ToString("o")
    snapshot_sha = $SnapshotSha
    search_query = $query
    search_api_total = $reportedTotal
    excluded_bot_authored_n = $botIssues.Count
    included_human_authored_n = $humanIssues.Count
    bot_rule = "Exclude when user.type is Bot, login ends [bot] or -bot, or login starts bot-."
    signal_rule = "First comment, label add/remove, close, or conversion by a non-author, non-bot human actor; null actors, issue authors, template automation, and bots are excluded before event classification."
    quartile_method = "R-7 / Excel PERCENTILE.INC linear interpolation; delay summaries use only issues with an observed signal."
    km_method = $km.summary.quantile_definition
}
Write-Utf8Json $metadata $metadataPath
Write-Utf8Json $summaries (Join-Path $OutputDirectory "summary.json")

$lines = @(
    "Apache Airflow issue-triage need metric",
    "Collected UTC: $($metadata.collected_at_utc)",
    "Window UTC: $($metadata.window_start_utc) through $($metadata.window_end_utc)",
    "Snapshot SHA for copied repository standards: $SnapshotSha",
    "Search population: $reportedTotal issues; excluded bot-authored: $($botIssues.Count); analysed: $($humanIssues.Count)",
    "",
    "Metric: time from issue creation to the first timeline comment, label change, close, or conversion by a non-author human.",
    "Whole-population Kaplan-Meier (n=$($km.summary.n), events=$($km.summary.events), right-censored=$($km.summary.right_censored)): Q1=$($km.summary.q1_hours) h; median=$($km.summary.median_hours) h; Q3=$($km.summary.q3_hours) h; S(48h)=$($km.summary.survival_at_48h); S(168h)=$($km.summary.survival_at_168h).",
    "KM quartiles are earliest event times where cumulative incidence reaches 25%, 50%, and 75%; an unreached quantile is null.",
    "Observed-delay quartiles below use only n=$($km.summary.events) issues with a signal; 2-day/7-day/never shares use the full n=$($km.summary.n) population.",
    ""
)
foreach ($summary in $summaries) {
    $observedText = if ($summary.n_observed_signal -gt 0) { "median=$($summary.median_hours_observed) h; IQR=$($summary.q1_hours_observed)-$($summary.q3_hours_observed) h; range=$($summary.min_hours_observed)-$($summary.max_hours_observed) h" } else { "median/IQR/range=n/a" }
    $shareText = if ($summary.n -gt 0) { ">2d=$($summary.still_untriaged_after_2d_n)/$($summary.n) ($($summary.still_untriaged_after_2d_pct)%); >7d=$($summary.still_untriaged_after_7d_n)/$($summary.n) ($($summary.still_untriaged_after_7d_pct)%); never=$($summary.never_human_signal_n)/$($summary.n) ($($summary.never_human_signal_pct)%)" } else { ">2d/>7d/never=n/a" }
    $lines += "[$($summary.group)] n=$($summary.n); observed=$($summary.n_observed_signal); $observedText; $shareText"
}
$lines += @(
    "",
    "Limitations:",
    "- Triage in Slack or mailing lists is invisible.",
    "- Template/bot labels are not human triage signals.",
    "- Discussions are a separate queue; converted issues can disappear from Issues search, so zero observed conversions may be an undercount.",
    "- Deleted spam issues are absent from Issues search, so the search population can undercount them.",
    "- Issue bodies can be edited after opening; this metric does not reconstruct the first body version.",
    "- Observed-delay summaries omit right-censored issues, so use them together with the never-signal share.",
    "- Actor-type and login-pattern bot detection may misclassify unusual automation or human accounts."
)
[System.IO.File]::WriteAllLines((Join-Path $OutputDirectory "results.txt"), $lines, [System.Text.UTF8Encoding]::new($false))
Write-Output ($lines -join "`n")
