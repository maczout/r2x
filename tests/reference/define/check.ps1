# Check r2x define against files made by hand in Response-2000 on Windows.
#
#   powershell -ExecutionPolicy Bypass -File check.ps1                 # every case with a hand.r2t
#   powershell -ExecutionPolicy Bypass -File check.ps1 -Cases quick-tbeam,long-modify
#   powershell -ExecutionPolicy Bypass -File check.ps1 -All            # also cases without one
#
# For each case (cases.json; how to make hand.r2t is in the case's README.md) it runs the case's
# session.txt in an r2x session in the case folder, which makes r2x.r2t (from a copy of Newbeam
# where the case starts from it) and its report r2x.r2x.html, then compares r2x.r2t with hand.r2t
# byte for byte. For a Quick Define case the date is left out of the comparison: Response dates
# a new section with the day it is made. The session's output is kept in r2x-session.log.
# Needs r2x installed and its image built (r2x health).
param(
    [string[]]$Cases = @(),
    [switch]$All
)

$names = @($Cases | ForEach-Object { $_ -split "," } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$newbeam = Join-Path $PSScriptRoot "..\newbeam\input.r2t"
$data = Get-Content -Raw -Encoding UTF8 (Join-Path $PSScriptRoot "cases.json") | ConvertFrom-Json
$datePattern = 'date(\s*)="\d{4}/\d{2}/\d{2}"'
$results = @()

foreach ($case in $data.cases) {
    if ($names.Count -and -not ($names -contains $case.name)) { continue }
    $dir = Join-Path $PSScriptRoot $case.name
    $hand = Join-Path $dir "hand.r2t"
    if (-not (Test-Path $hand) -and -not $All) {
        Write-Host "$($case.name): no hand.r2t yet (see its README.md), skipped"
        continue
    }
    Push-Location $dir
    $verdict = $null
    try {
        Remove-Item r2x.r2t, r2x.r2x.html, r2x.r2x.txt, r2x-session.log -ErrorAction SilentlyContinue
        if ($case.from -eq "newbeam") { Copy-Item $newbeam r2x.r2t }
        $started = Get-Date
        # stderr (progress) goes to the log too; in Windows PowerShell keep its lines as text
        Get-Content session.txt | r2x 2>&1 | ForEach-Object { "$_" } | Out-File -Encoding utf8 r2x-session.log
        $seconds = ((Get-Date) - $started).TotalSeconds
        if (-not (Test-Path r2x.r2t)) {
            $verdict = "FAILED (no r2x.r2t; see r2x-session.log)"
        } elseif (-not (Test-Path hand.r2t)) {
            $verdict = "made r2x.r2t; no hand.r2t to compare"
        } else {
            $a = [IO.File]::ReadAllBytes((Resolve-Path hand.r2t))
            $b = [IO.File]::ReadAllBytes((Resolve-Path r2x.r2t))
            $same = ($a.Length -eq $b.Length) -and -not (Compare-Object $a $b -SyncWindow 0)
            if (-not $same -and -not $case.from) {
                # Quick Define: the same but for the date?
                $ta = [Text.Encoding]::ASCII.GetString($a) -replace $datePattern, 'date$1="-"'
                $tb = [Text.Encoding]::ASCII.GetString($b) -replace $datePattern, 'date$1="-"'
                if ($ta -ceq $tb) { $verdict = "MATCH but for the date" }
            }
            if ($same) { $verdict = "MATCH byte for byte" }
            elseif (-not $verdict) {
                $verdict = "DIFFERS (fc.exe /n hand.r2t r2x.r2t shows where)"
            }
        }
        $line = "{0}: {1} ({2:N0} s)" -f $case.name, $verdict, $seconds
        Write-Host $line
        $results += $line
    } finally {
        Pop-Location
    }
}
if ($results.Count) {
    $results | Out-File -Encoding utf8 (Join-Path $PSScriptRoot "check-results.txt")
}
