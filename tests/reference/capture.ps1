# Save hand-copied Response-2000 chart data into the current reference case folder.
# For each file: right-click the named chart in Response -> Copy Chart Data, then press Enter here.
# Writes the clipboard text exactly as Response put it (ASCII, CRLF, no added newline).
#
#   powershell -ExecutionPolicy Bypass -File ..\capture.ps1              # detail views: stages\peak
#   powershell -ExecutionPolicy Bypass -File ..\capture.ps1 -Stage 056   # or a known stage number
#
# Response shows no stage number. Detail views of the stage it opens on after solving go to
# stages\peak; that folder is renamed to the stage number once its curvature has been matched to
# the Moment-phi curve.
param([string]$Stage = "peak")

$files = [ordered]@{
    "control\moment_ex.txt"                         = "Control : Moment - ex   (top-left control chart)"
    "control\moment_phi.txt"                        = "Control : Moment - phi  (bottom-left control chart)"
    "stages\$Stage\longitudinal_strain.txt"          = "Longitudinal Strain"
    "stages\$Stage\shrinkage_thermal_strain.txt"     = "Shrinkage & Thermal Strain"
    "stages\$Stage\long_reinforcement_stress.txt"    = "Long. Reinforcement Stress"
    "stages\$Stage\long_reinf_stress_at_crack.txt"   = "Long. Reinf Stress at Crack"
    "stages\$Stage\longitudinal_concrete_stress.txt" = "Longitudinal Concrete Stress"
}

$previous = $null
foreach ($path in $files.Keys) {
    while ($true) {
        $answer = Read-Host "Copy Chart Data from '$($files[$path])', then press Enter (s to skip)"
        if ($answer -eq "s") {
            Write-Warning "skipped $path"
            break
        }
        $text = Get-Clipboard -Raw
        if (-not $text -or -not $text.Contains("Data from Graph")) {
            Write-Warning "Clipboard does not look like chart data; copy it again"
            continue
        }
        if ($text -ceq $previous) {
            Write-Warning "Clipboard is unchanged since the last chart (did Copy Chart Data run?); copy it again"
            continue
        }
        $previous = $text
        $title = ($text -split "`r?`n" | Where-Object { $_ -match "^\s*Title\s*:" } | Select-Object -First 1)
        New-Item -ItemType Directory -Force -Path (Split-Path $path) | Out-Null
        [System.IO.File]::WriteAllText((Join-Path (Get-Location) $path), $text, [System.Text.Encoding]::ASCII)
        Write-Host "  saved $path   [$("$title".Trim())]"
        break
    }
}
