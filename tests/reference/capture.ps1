# Save hand-copied Response-2000 chart data into the current reference case folder.
# For each file: right-click the named chart in Response -> Copy Chart Data, then press Enter here.
# Writes the clipboard text exactly as Response put it (ASCII, CRLF, no added newline).

$files = [ordered]@{
    "control\moment_ex.txt"                       = "Control : Moment - ex   (top-left control chart)"
    "control\moment_phi.txt"                      = "Control : Moment - phi  (bottom-left control chart)"
    "stages\056\longitudinal_strain.txt"          = "Longitudinal Strain"
    "stages\056\shrinkage_thermal_strain.txt"     = "Shrinkage & Thermal Strain"
    "stages\056\long_reinforcement_stress.txt"    = "Long. Reinforcement Stress"
    "stages\056\long_reinf_stress_at_crack.txt"   = "Long. Reinf Stress at Crack"
    "stages\056\longitudinal_concrete_stress.txt" = "Longitudinal Concrete Stress"
}

foreach ($path in $files.Keys) {
    $null = Read-Host "Copy Chart Data from '$($files[$path])', then press Enter"
    $text = Get-Clipboard -Raw
    if (-not $text -or -not $text.Contains("Data from Graph")) {
        Write-Warning "Clipboard does not look like chart data; skipped $path"
        continue
    }
    $title = ($text -split "`r?`n" | Where-Object { $_ -match "^\s*Title\s*:" } | Select-Object -First 1)
    New-Item -ItemType Directory -Force -Path (Split-Path $path) | Out-Null
    [System.IO.File]::WriteAllText((Join-Path (Get-Location) $path), $text, [System.Text.Encoding]::ASCII)
    Write-Host "  saved $path   [$("$title".Trim())]"
}
