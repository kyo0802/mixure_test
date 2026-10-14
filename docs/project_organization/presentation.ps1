$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$shell = New-Object -ComObject WScript.Shell
$spec = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'shortcuts.json') -Raw | ConvertFrom-Json
$verified = @()
foreach ($entry in $spec) {
    $target = Join-Path $repo $entry.target
    if (-not (Test-Path -LiteralPath $target)) { throw "Missing target: $target" }
    $shortcut = $shell.CreateShortcut((Join-Path $repo $entry.link))
    $shortcut.TargetPath = $target
    $shortcut.WorkingDirectory = $repo
    $shortcut.Description = 'FindMind authoritative original; this is not a copy'
    $shortcut.Save()
    $check = $shell.CreateShortcut((Join-Path $repo $entry.link))
    if ($check.TargetPath -ne $target) { throw 'Shortcut target mismatch' }
    $verified += @{link=$entry.link;target=$entry.target;valid=$true}
}
$verified | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'shortcut_verification.json') -Encoding utf8
$baseline = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'before.json') -Raw | ConvertFrom-Json
$names = @($baseline.moves.old) + @($baseline.blocked.path) + @(
    '.models','.pytest_cache','.runtime','.sam2_deps','.sam2_official','.uv-cache','.venv',
    'artifacts','outputs','annotation_handoff','annotation_returns','val_set','Ultralytics',
    'README.md','README_V2.md','README_V21.md','CURRENT_PIPELINE.md','V2_VALIDATION.md','V21_VALIDATION.md','VALIDATION.md',
    'yolo11s.pt'
) + @(1..9 | ForEach-Object {"test$_.mp4"})
$changes = @()
foreach ($name in $names) {
    $path = Join-Path $repo $name
    try {
        $item = Get-Item -LiteralPath $path -Force
        $previous = [int]$item.Attributes
        $item.Attributes = $item.Attributes -bor [IO.FileAttributes]::Hidden
        $changes += @{path=$name;before=$previous;after=[int](Get-Item -LiteralPath $path -Force).Attributes;status='hidden'}
    } catch {
        $changes += @{path=$name;status='unchanged_access_denied';reason=$_.Exception.Message}
    }
}
$changes | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'visibility_changes.json') -Encoding utf8
Write-Output "Validated $($verified.Count) shortcuts; recorded $($changes.Count) visibility entries."
