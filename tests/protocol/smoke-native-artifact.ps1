param(
    [Parameter(Mandatory = $true)]
    [string]$Artifact
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$Artifact = (Resolve-Path $Artifact).Path
$Temp = Join-Path ([System.IO.Path]::GetTempPath()) ("harness-protocol-" + [guid]::NewGuid())
$Db = Join-Path $Temp "harness.db"

function Invoke-HarnessJson {
    param(
        [string[]]$Arguments,
        [int]$ExpectedExit = 0
    )
    $stderr = Join-Path $Temp ("stderr-" + [guid]::NewGuid() + ".txt")
    $lines = @(& $Artifact @Arguments 2>$stderr)
    $exit = $LASTEXITCODE
    if ($exit -ne $ExpectedExit) {
        $detail = if (Test-Path $stderr) { Get-Content -Raw $stderr } else { "" }
        $text = $lines -join "`n"
        throw "Harness '$($Arguments -join ' ')' exited $exit, expected $ExpectedExit. stdout=$text stderr=$detail"
    }
    $text = $lines -join "`n"
    try { return $text | ConvertFrom-Json -Depth 100 }
    catch { throw "Harness did not emit one JSON document: $text" }
}

try {
    New-Item -ItemType Directory -Force (Join-Path $Temp "scripts") | Out-Null
    Copy-Item -Recurse (Join-Path $RepoRoot "scripts/schema") (Join-Path $Temp "scripts/schema")
    $env:HARNESS_REPO_ROOT = $Temp
    $env:HARNESS_DB_PATH = $Db

    $contract = Invoke-HarnessJson -Arguments @("query", "contract", "--json")
    if ($contract.result.database_state -ne "missing" -or (Test-Path $Db)) {
        throw "Missing-database discovery mutated state or reported the wrong state"
    }

    & $Artifact init | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "harness init failed" }
    $null = Invoke-HarnessJson -Arguments @("story", "add", "--id", "US-A", "--title", "Alpha", "--lane", "normal", "--verify", "true", "--json")
    $null = Invoke-HarnessJson -Arguments @("story", "add", "--id", "US-B", "--title", "Beta", "--lane", "normal", "--verify", "true", "--json")

    $querySqlRead = @(& $Artifact query sql "WITH selected AS (SELECT id FROM story WHERE id='US-A') SELECT id FROM selected;") -join "`n"
    if ($LASTEXITCODE -ne 0 -or -not $querySqlRead.Contains("US-A")) {
        throw "Read-only query SQL did not return the sentinel story"
    }
    $querySqlWriteStderr = Join-Path $Temp "query-sql-write.stderr"
    $env:HARNESS_RUN_ID = "protocol_query_sql_write"
    & $Artifact query sql "WITH doomed AS (SELECT id FROM story WHERE id='US-A') DELETE FROM story WHERE id IN (SELECT id FROM doomed) RETURNING id;" 2>$querySqlWriteStderr | Out-Null
    $querySqlWriteExit = $LASTEXITCODE
    Remove-Item Env:HARNESS_RUN_ID -ErrorAction SilentlyContinue
    if ($querySqlWriteExit -ne 1 -or -not (Get-Content -Raw $querySqlWriteStderr).Contains("query sql is read-only")) {
        throw "Query SQL accepted a mutating CTE"
    }
    $querySqlChangeset = Join-Path $Temp ".harness/changesets/protocol_query_sql_write.changeset.jsonl"
    if (Test-Path $querySqlChangeset) { throw "Rejected query SQL write emitted a semantic changeset" }
    $querySqlStories = Invoke-HarnessJson -Arguments @("query", "stories", "--json")
    if (($querySqlStories.result.stories | Where-Object id -eq "US-A").title -ne "Alpha") {
        throw "Rejected query SQL write changed story state"
    }

    $null = Invoke-HarnessJson -Arguments @("story", "dependency", "add", "--blocker", "US-A", "--blocked", "US-B", "--json")
    $null = Invoke-HarnessJson -Arguments @("story", "hierarchy", "add", "--parent", "US-A", "--child", "US-B", "--json")
    $graph = Invoke-HarnessJson -Arguments @("query", "work-graph", "--json")
    if ($graph.result.revision.Length -ne 64 -or $graph.result.dependencies.Count -ne 1 -or $graph.result.hierarchy.Count -ne 1) {
        throw "Work graph is incomplete or has no stable revision"
    }

    $textBypassStderr = Join-Path $Temp "text-bypass.stderr"
    & $Artifact story update --id US-A --status implemented 2>$textBypassStderr | Out-Null
    if ($LASTEXITCODE -ne 1 -or -not (Get-Content -Raw $textBypassStderr).Contains("status 'implemented' is completion-only")) {
        throw "Human-readable story update did not reject the completion bypass"
    }
    $casBypass = Invoke-HarnessJson -Arguments @("story", "update", "--id", "US-A", "--status", "implemented", "--expected-status", "planned", "--require-runnable", "--json") -ExpectedExit 2
    if ($casBypass.error.code -ne "INVALID_ARGUMENT" -or -not $casBypass.error.message.Contains("story complete US-A")) {
        throw "Machine story update did not reject the completion bypass"
    }
    $unchangedStories = Invoke-HarnessJson -Arguments @("query", "stories", "--json")
    if (($unchangedStories.result.stories | Where-Object id -eq "US-A").status -ne "planned") {
        throw "Rejected completion bypass changed story state"
    }

    $cas = Invoke-HarnessJson -Arguments @("story", "update", "--id", "US-A", "--status", "in_progress", "--expected-status", "planned", "--require-runnable", "--json")
    if ($cas.result.before_status -ne "planned" -or $cas.result.after_status -ne "in_progress") {
        throw "CAS result did not report the transition"
    }
    $complete = Invoke-HarnessJson -Arguments @("story", "complete", "US-A", "--json")
    if ($complete.result.result -ne "pass") { throw "Explicit story completion did not pass" }
    $conflict = Invoke-HarnessJson -Arguments @("story", "hierarchy", "add", "--parent", "US-B", "--child", "US-A", "--json") -ExpectedExit 3
    if ($conflict.error.code -ne "CONFLICT") { throw "Hierarchy cycle was not a stable conflict" }

    $changeset = Join-Path $Temp "protocol-smoke.jsonl"
    '{"base_schema_version":14,"op":"changeset.header","run_id":"protocol_smoke","version":1}' | Set-Content -Encoding utf8NoBOM $changeset
    $status = Invoke-HarnessJson -Arguments @("db", "changeset", "status", $changeset, "--json")
    if ($status.result.applied) { throw "Fresh changeset unexpectedly reported applied" }
    $apply = Invoke-HarnessJson -Arguments @("db", "changeset", "apply", $changeset, "--json")
    if (-not $apply.result.applied -or $apply.result.content_sha256.Length -ne 64) { throw "Changeset apply result is incomplete" }

    $stale = Join-Path $Temp "protocol-stale.jsonl"
    @(
        '{"base_schema_version":14,"op":"changeset.header","run_id":"protocol_stale","version":1}'
        '{"op":"story.update","version":3,"id":"US-A","expected_revision":0,"payload":{"status":"changed"}}'
    ) | Set-Content -Encoding utf8NoBOM $stale
    $staleResult = Invoke-HarnessJson -Arguments @("db", "changeset", "apply", $stale, "--json") -ExpectedExit 3
    if ($staleResult.error.code -ne "CONFLICT" -or
        $staleResult.error.details.changeset_id -ne "protocol_stale" -or
        $staleResult.error.details.entity_kind -ne "story" -or
        $staleResult.error.details.entity_id -ne "US-A" -or
        $staleResult.error.details.expected_revision -ne 0 -or
        $staleResult.error.details.actual_revision -ne 2) {
        throw "Revision conflict envelope is incomplete"
    }

    $SnapshotDir = Join-Path $Temp "path with spaces"
    New-Item -ItemType Directory -Force $SnapshotDir | Out-Null
    $Snapshot = Join-Path $SnapshotDir "snapshot.db"
    $snapshotResult = Invoke-HarnessJson -Arguments @("db", "snapshot", "--output", $Snapshot, "--json")
    if ($snapshotResult.result.snapshot_file_sha256.Length -ne 64 -or -not (Test-Path $Snapshot)) {
        throw "Snapshot result is incomplete"
    }
    $env:HARNESS_DB_PATH = $Snapshot
    $snapshotContract = Invoke-HarnessJson -Arguments @("query", "contract", "--json")
    if ($snapshotContract.result.database_state -ne "current") { throw "Snapshot is not readable as a current Harness DB" }

    Write-Host "protocol-v1 PowerShell artifact smoke passed"
}
finally {
    Remove-Item Env:HARNESS_REPO_ROOT -ErrorAction SilentlyContinue
    Remove-Item Env:HARNESS_DB_PATH -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $Temp -ErrorAction SilentlyContinue
}
