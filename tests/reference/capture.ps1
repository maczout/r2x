# Save hand-copied Response-2000 chart data into the current reference case folder.
# For each file: right-click the named chart in Response -> Copy Chart Data, then press Enter here.
# Writes the clipboard text exactly as Response put it (ASCII, CRLF, no added newline).
#
#   powershell -ExecutionPolicy Bypass -File ..\capture.ps1              # detail views: stages\peak
#   powershell -ExecutionPolicy Bypass -File ..\capture.ps1 -Stage 056   # or a known stage number
#   powershell -ExecutionPolicy Bypass -File ..\capture.ps1 -Views no-shear,cracking
#
# The control charts, the detail views and their charts come from r2x's catalogue,
# src\r2x\views.json. The script asks for the two control charts first and names each file by
# its title (control\moment_phi.txt, control\shear_gxy.txt, ...), then for each view in turn
# (switch Response's view list, under "Nine Graphs", when it says),
# then for each chart in it with a data export; a chart that recurs in several views is asked for
# once. Files that already exist are kept and not asked for again, so the script can be rerun to
# fill gaps. Change views with the list only: paging (PgUp/PgDn) changes the stage.
#
# Response shows no stage number. Detail views of the stage it opens on after solving go to
# stages\peak; that folder is renamed to the stage number once its strain profile has been
# matched to the control curves (curvature to Moment-phi, or ex to an ex curve).
param(
    [string]$Stage = "peak",
    [string[]]$Views = @("all")
)

$catalogue = Join-Path $PSScriptRoot "..\..\src\r2x\views.json"
$data = Get-Content -Raw -Encoding UTF8 $catalogue | ConvertFrom-Json
$known = $data.views
$controlKeys = @{}
foreach ($c in $data.controls) { $controlKeys[$c.title] = $c.key }
$names = @($Views | ForEach-Object { $_ -split "," } | ForEach-Object { $_.Trim().ToLower() })
if ($names -contains "all") { $names = @($known | ForEach-Object { $_.name }) }
foreach ($n in $names) {
    if (-not ($known | Where-Object { $_.name -eq $n })) {
        throw "Unknown view '$n': use all, or any of $(($known | ForEach-Object { $_.name }) -join ', ')"
    }
}

$script:previous = $null

# Ask for one chart until the clipboard holds new chart data (with this title, if one is given),
# then save it. Returns $false if the user skips it.
function Save-Chart([string]$path, [string]$label, [string]$title) {
    while ($true) {
        $answer = Read-Host "Copy Chart Data from '$label', then press Enter (s to skip)"
        if ($answer -eq "s") {
            Write-Warning "skipped $path"
            return $false
        }
        $text = Get-Clipboard -Raw
        if (-not $text -or -not $text.Contains("Data from Graph")) {
            Write-Warning "Clipboard does not look like chart data; copy it again"
            continue
        }
        if ($text -ceq $script:previous) {
            Write-Warning "Clipboard is unchanged since the last chart (did Copy Chart Data run?); copy it again"
            continue
        }
        $line = ($text -split "`r?`n" | Where-Object { $_ -match "^\s*Title\s*:" } | Select-Object -First 1)
        $got = "$line" -replace "^\s*Title\s*:\s*", ""
        if ($title -and $got.Trim() -cne $title) {
            Write-Warning "That is '$($got.Trim())', not '$title' (wrong chart, or the view list not switched?); copy it again"
            continue
        }
        $script:previous = $text
        New-Item -ItemType Directory -Force -Path (Split-Path $path) | Out-Null
        [System.IO.File]::WriteAllText((Join-Path (Get-Location) $path), $text, [System.Text.Encoding]::ASCII)
        Write-Host "  saved $path   [$($got.Trim())]"
        return $true
    }
}

function Test-Have([string]$path) {
    if (Test-Path $path) {
        Write-Host "  have  $path"
        return $true
    }
    return $false
}

# Control charts: which two Response shows depends on the increment (Moment-ex and Moment-phi,
# Shear-gxy above Moment-phi, ...), so each file is named from the title it exports. With an axial
# load alone both are Axial Load-ex, kept once.
function Save-Control([string]$position, [string]$top) {
    while ($true) {
        $answer = Read-Host "Copy Chart Data from the $position control chart (left of the view), then press Enter (s to skip)"
        if ($answer -eq "s") {
            Write-Warning "skipped the $position control chart"
            return $null
        }
        $text = Get-Clipboard -Raw
        if (-not $text -or -not $text.Contains("Data from Graph")) {
            Write-Warning "Clipboard does not look like chart data; copy it again"
            continue
        }
        $line = ($text -split "`r?`n" | Where-Object { $_ -match "^\s*Title\s*:" } | Select-Object -First 1)
        $got = ("$line" -replace "^\s*Title\s*:\s*", "").Trim()
        if (-not $controlKeys.ContainsKey($got)) {
            Write-Warning "'$got' is not a control chart r2x knows ($(($controlKeys.Keys) -join '; ')); copy it again"
            continue
        }
        $key = $controlKeys[$got]
        if ($top -and $key -eq $top) {
            if ($text -ceq $script:previous) {
                Write-Host "  same chart as the top one ($key): one file"
                return $key
            }
            Write-Warning "Both control charts are '$got' but their data differ; copy the $position one again"
            continue
        }
        if ($text -ceq $script:previous) {
            Write-Warning "Clipboard is unchanged since the last chart (did Copy Chart Data run?); copy it again"
            continue
        }
        $path = "control\$key.txt"
        $script:previous = $text
        New-Item -ItemType Directory -Force -Path "control" | Out-Null
        [System.IO.File]::WriteAllText((Join-Path (Get-Location) $path), $text, [System.Text.Encoding]::ASCII)
        Write-Host "  saved $path   [$got]"
        return $key
    }
}

$haveControls = @(Get-ChildItem -Path "control" -Filter "*.txt" -ErrorAction SilentlyContinue | ForEach-Object { $_.BaseName })
if ($haveControls.Count -ge 2 -or ($haveControls.Count -eq 1 -and $haveControls[0] -eq "axial_ex")) {
    Write-Host "  have  control\ ($($haveControls -join ', '))"
} else {
    $top = Save-Control "top" $null
    Save-Control "bottom" $top | Out-Null
}

# Detail views, in the catalogue's order.
$asked = @{}
foreach ($view in $known) {
    if ($names -notcontains $view.name) { continue }
    $todo = @()
    foreach ($chart in $view.charts) {
        if ($asked.ContainsKey($chart.key)) { continue }
        $asked[$chart.key] = $true
        $path = "stages\$Stage\$($chart.key).txt"
        if (-not (Test-Have $path)) { $todo += , @($path, $chart) }
    }
    if ($todo.Count -eq 0) { continue }
    Read-Host "Switch Response's view list to '$($view.response)', then press Enter" | Out-Null
    foreach ($item in $todo) {
        $chart = $item[1]
        $label = "$($chart.title)  (row $($chart.grid[0]), column $($chart.grid[1]))"
        Save-Chart $item[0] $label $chart.title | Out-Null
    }
}
