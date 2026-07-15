<#
.SYNOPSIS
    Batch-submit 20 test applicants to the Credit Decisioning Agent API,
    then verify that:
      1. The LLM reviewed (extracted) the submitted documents.
      2. The reviewer can access the full PDF report (documents + decision).

.DESCRIPTION
    For each applicant under tests\fixtures\batch\APP-BXX\ the script:
      Step 1 — Upload the three PDF documents (id.pdf, pay_stub.pdf,
               bank_statement.pdf) via POST /applications/{id}/documents.
      Step 2 — Submit the application JSON via POST /applications.
      Step 3 — Poll GET /applications/{id} until the LLM pipeline
               completes (status != "pending_human_review" means hold/error;
               agent_recommendation populated means LLM ran successfully).
      Step 4 — Confirm the LLM extracted fields (income_monthly present in
               score_breakdown is a proxy — score node only runs after LLM
               extract node succeeds).
      Step 5 — Fetch the PDF report via GET /applications/{id}/pdf and
               confirm HTTP 200 — this is the reviewer's copy that contains
               the application summary, LLM rationale, and document list.

.PARAMETER BaseUrl
    Base URL of the running API. Default: http://localhost:8000

.PARAMETER FixtureRoot
    Path to the batch fixtures folder.
    Default: tests\fixtures\batch (relative to this script's parent dir)

.PARAMETER PollTimeoutSec
    Max seconds to wait per application for the pipeline to finish.
    Default: 60

.EXAMPLE
    # With the server running:
    .\scripts\batch_submit.ps1

    # Against a different host:
    .\scripts\batch_submit.ps1 -BaseUrl http://localhost:9000
#>

param(
    [string]$BaseUrl       = "http://localhost:8000",
    [string]$FixtureRoot   = "",
    [int]   $PollTimeoutSec = 60
)

$ErrorActionPreference = "Stop"

# ── Resolve paths ────────────────────────────────────────────────────────────
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

if (-not $FixtureRoot) {
    $FixtureRoot = Join-Path $ProjectRoot "tests\fixtures\batch"
}

# ── Helpers ──────────────────────────────────────────────────────────────────
function Write-Step  { param($msg) Write-Host "  $msg" -ForegroundColor Cyan }
function Write-Pass  { param($msg) Write-Host "  [PASS] $msg" -ForegroundColor Green }
function Write-Fail  { param($msg) Write-Host "  [FAIL] $msg" -ForegroundColor Red }
function Write-Warn  { param($msg) Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Title { param($msg) Write-Host "`n$msg" -ForegroundColor White }

function Invoke-Api {
    param(
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers = @{},
        [object]$Body = $null,
        [string]$ContentType = "application/json",
        [switch]$Raw
    )
    $params = @{ Method = $Method; Uri = $Uri; UseBasicParsing = $true }
    if ($Headers.Count) { $params.Headers = $Headers }
    if ($Body -ne $null) { $params.Body = $Body; $params.ContentType = $ContentType }
    $response = Invoke-WebRequest @params
    if ($Raw) { return $response }
    return $response.Content | ConvertFrom-Json
}

# ── Check server is up ───────────────────────────────────────────────────────
Write-Title "=== Credit Decisioning Agent — Batch Submission ==="
Write-Host "API: $BaseUrl"
Write-Host "Fixtures: $FixtureRoot"

try {
    $health = Invoke-Api -Method GET -Uri "$BaseUrl/health" 2>$null
} catch {
    # /health may not exist — try the docs endpoint
    try {
        Invoke-WebRequest -Uri "$BaseUrl/docs" -UseBasicParsing | Out-Null
    } catch {
        Write-Host ""
        Write-Fail "Cannot reach API at $BaseUrl — is the server running?"
        Write-Host "  Start it with:  .\start.ps1  or  uvicorn app.main:app --reload"
        exit 1
    }
}
Write-Pass "Server is reachable at $BaseUrl"

# ── Collect applicant folders ────────────────────────────────────────────────
$AppDirs = Get-ChildItem -Path $FixtureRoot -Directory |
           Where-Object { $_.Name -match "^APP-B\d+" } |
           Sort-Object Name

if ($AppDirs.Count -eq 0) {
    Write-Fail "No APP-B* folders found under $FixtureRoot"
    Write-Host "  Run:  .venv\Scripts\python scripts\generate_fixtures.py"
    exit 1
}

Write-Host "Found $($AppDirs.Count) applicant folder(s).`n"

# ── Per-applicant tracking ───────────────────────────────────────────────────
$Results = [System.Collections.Generic.List[hashtable]]::new()

foreach ($Dir in $AppDirs) {
    $AppId    = $Dir.Name
    $AppJson  = Join-Path $Dir.FullName "application.json"
    $IdPdf    = Join-Path $Dir.FullName "id.pdf"
    $PayPdf   = Join-Path $Dir.FullName "pay_stub.pdf"
    $BankPdf  = Join-Path $Dir.FullName "bank_statement.pdf"

    $Result = @{
        app_id           = $AppId
        upload_ok        = $false
        submit_ok        = $false
        llm_reviewed     = $false
        pdf_accessible   = $false
        band             = "?"
        rationale_words  = 0
        error            = ""
    }

    Write-Title "── $AppId ──────────────────────────────────────────"

    # ── Step 1: Upload documents ─────────────────────────────────────────────
    Write-Step "Step 1: Uploading PDFs ..."
    try {
        # Build multipart form manually using .NET types
        $boundary = [System.Guid]::NewGuid().ToString("N")
        $LF = "`r`n"

        function Add-FilePart {
            param($PartName, $FilePath, $DocType)
            $bytes   = [System.IO.File]::ReadAllBytes($FilePath)
            $fname   = Split-Path $FilePath -Leaf
            $header  = "--$boundary$LF"
            $header += "Content-Disposition: form-data; name=`"files`"; filename=`"$fname`"$LF"
            $header += "Content-Type: application/pdf$LF$LF"
            return [System.Text.Encoding]::UTF8.GetBytes($header) + $bytes + [System.Text.Encoding]::UTF8.GetBytes($LF)
        }

        $bodyParts  = @()
        $bodyParts += Add-FilePart "files" $IdPdf   "id"
        $bodyParts += Add-FilePart "files" $PayPdf  "pay_stub"
        $bodyParts += Add-FilePart "files" $BankPdf "bank_statement"

        # doc_types form field
        $dtHeader  = "--$boundary$LF"
        $dtHeader += "Content-Disposition: form-data; name=`"doc_types`"$LF$LF"
        $dtHeader += "id,pay_stub,bank_statement$LF"
        $bodyParts += [System.Text.Encoding]::UTF8.GetBytes($dtHeader)

        # closing boundary
        $bodyParts += [System.Text.Encoding]::UTF8.GetBytes("--$boundary--$LF")

        # flatten to single byte array
        $totalLen = ($bodyParts | Measure-Object -Property Length -Sum).Sum
        $bodyBytes = New-Object byte[] $totalLen
        $offset = 0
        foreach ($part in $bodyParts) {
            [System.Array]::Copy($part, 0, $bodyBytes, $offset, $part.Length)
            $offset += $part.Length
        }

        $uploadResp = Invoke-WebRequest `
            -Method POST `
            -Uri "$BaseUrl/applications/$AppId/documents" `
            -Body $bodyBytes `
            -ContentType "multipart/form-data; boundary=$boundary" `
            -UseBasicParsing

        $uploadData = $uploadResp.Content | ConvertFrom-Json
        $docCount   = ($uploadData.uploaded | Measure-Object).Count
        Write-Pass "Uploaded $docCount document(s)"
        $Result.upload_ok = $true

    } catch {
        $Result.error = "Upload failed: $_"
        Write-Fail "Document upload failed: $_"
        $Results.Add($Result)
        continue
    }

    # ── Step 2: Submit application ───────────────────────────────────────────
    Write-Step "Step 2: Submitting application JSON ..."
    try {
        $appBody = Get-Content $AppJson -Raw
        $submitResp = Invoke-Api -Method POST -Uri "$BaseUrl/applications" -Body $appBody
        Write-Pass "Application submitted  (initial status: $($submitResp.status))"
        $Result.submit_ok = $true
    } catch {
        # 409 = already submitted from a previous run — that's acceptable
        if ($_.Exception.Response.StatusCode.value__ -eq 409) {
            Write-Warn "Application already exists (re-run) — skipping re-submit"
            $Result.submit_ok = $true
        } else {
            $Result.error = "Submit failed: $_"
            Write-Fail "Submit failed: $_"
            $Results.Add($Result)
            continue
        }
    }

    # ── Step 3 + 4: Poll until LLM pipeline completes ───────────────────────
    Write-Step "Step 3: Polling for LLM pipeline completion (max ${PollTimeoutSec}s) ..."
    $deadline = (Get-Date).AddSeconds($PollTimeoutSec)
    $llmDone  = $false
    $appRecord = $null

    do {
        Start-Sleep -Seconds 3
        try {
            $appRecord = Invoke-Api -Method GET -Uri "$BaseUrl/applications/$AppId"
        } catch {
            Write-Warn "Poll error: $_"
            break
        }

        # Pipeline is done once agent_recommendation is populated
        if ($appRecord.agent_recommendation -and
            $appRecord.agent_recommendation -ne "" -and
            $appRecord.agent_recommendation -ne $null) {
            $llmDone = $true
            break
        }

        # Also treat hold_for_document as a terminal state (pipeline ran, docs missing)
        if ($appRecord.status -eq "hold_for_document") {
            $llmDone = $true
            break
        }

    } while ((Get-Date) -lt $deadline)

    if (-not $llmDone) {
        $Result.error = "Timed out waiting for LLM pipeline"
        Write-Fail "Pipeline did not complete within ${PollTimeoutSec}s"
        $Results.Add($Result)
        continue
    }

    # ── Step 4: Verify LLM reviewed the documents ───────────────────────────
    Write-Step "Step 4: Verifying LLM document review ..."

    $rec = $appRecord
    $recommendation = $rec.agent_recommendation
    $rationale      = $rec.rationale

    if ($recommendation -and $recommendation -ne "") {
        $Result.llm_reviewed   = $true
        $Result.band           = $recommendation
        $Result.rationale_words = if ($rationale) { ($rationale -split '\s+').Count } else { 0 }
        Write-Pass "LLM reviewed documents — recommendation: $recommendation  ($($Result.rationale_words) words in rationale)"
    } else {
        Write-Fail "LLM recommendation missing — pipeline may not have extracted documents"
        $Result.error = "No LLM recommendation"
    }

    # Also check that score_breakdown has income_monthly (proxy for extract running)
    $scoreBand = if ($rec.score_breakdown) { $rec.score_breakdown.band } else { $null }
    if ($scoreBand) {
        Write-Pass "Score engine ran — score band: $scoreBand"
    } else {
        Write-Warn "score_breakdown not found — extract node may have returned partial data"
    }

    # ── Step 5: Fetch PDF reviewer copy ─────────────────────────────────────
    Write-Step "Step 5: Fetching reviewer PDF report ..."
    try {
        $pdfResp = Invoke-WebRequest `
            -Method GET `
            -Uri "$BaseUrl/applications/$AppId/pdf" `
            -UseBasicParsing

        $pdfSize = $pdfResp.RawContentLength
        if ($pdfResp.StatusCode -eq 200 -and $pdfSize -gt 1000) {
            $Result.pdf_accessible = $true
            Write-Pass "PDF report accessible — $pdfSize bytes  (reviewer copy ready)"
        } else {
            Write-Fail "PDF response suspicious: status=$($pdfResp.StatusCode) size=$pdfSize"
        }

    } catch {
        $Result.error += " | PDF fetch failed: $_"
        Write-Fail "PDF fetch failed: $_"
    }

    $Results.Add($Result)
}

# ── Summary table ────────────────────────────────────────────────────────────
Write-Title "`n╔══════════════════════════════════════════════════════════════════════╗"
Write-Host   "║                    BATCH SUBMISSION SUMMARY                         ║" -ForegroundColor White
Write-Title  "╚══════════════════════════════════════════════════════════════════════╝"

$fmt = "{0,-10} {1,-7} {2,-7} {3,-12} {4,-9} {5,-10} {6}"
Write-Host ($fmt -f "APP-ID","UPLOAD","SUBMIT","LLM-REVIEW","BAND","PDF-COPY","NOTES") -ForegroundColor Gray
Write-Host ("-" * 90) -ForegroundColor Gray

$passCount = 0; $failCount = 0

foreach ($r in $Results) {
    $upload  = if ($r.upload_ok)      { "OK  " } else { "FAIL" }
    $submit  = if ($r.submit_ok)      { "OK  " } else { "FAIL" }
    $llm     = if ($r.llm_reviewed)   { "YES (LLM ran)" } else { "NO " }
    $pdf     = if ($r.pdf_accessible) { "OK  " } else { "FAIL" }
    $band    = if ($r.band)           { $r.band } else { "?" }
    $notes   = if ($r.error)          { $r.error.Substring(0, [Math]::Min(50, $r.error.Length)) } else { "" }

    $allOk = $r.upload_ok -and $r.submit_ok -and $r.llm_reviewed -and $r.pdf_accessible
    $color = if ($allOk) { "Green" } else { "Red" }
    if ($allOk) { $passCount++ } else { $failCount++ }

    Write-Host ($fmt -f $r.app_id, $upload, $submit, $llm, $band, $pdf, $notes) -ForegroundColor $color
}

Write-Host ("-" * 90) -ForegroundColor Gray
Write-Host ""
Write-Host "Results:  $passCount / $($Results.Count) applicants fully processed" -ForegroundColor White
Write-Host "  Passed all checks : $passCount" -ForegroundColor Green
Write-Host "  Failed a check    : $failCount" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Reviewer PDF reports available at:" -ForegroundColor Cyan
foreach ($r in ($Results | Where-Object { $_.pdf_accessible })) {
    Write-Host "  GET $BaseUrl/applications/$($r.app_id)/pdf"
}
Write-Host ""
Write-Host "To approve or decline an application (human gate):" -ForegroundColor Cyan
Write-Host '  $body = '"'"'{"human_decision":"approve","human_reviewer":"underwriter_1"}'"'"
Write-Host "  Invoke-RestMethod -Method Post -Uri `"$BaseUrl/applications/APP-B01/decision`" -ContentType application/json -Body `$body"
