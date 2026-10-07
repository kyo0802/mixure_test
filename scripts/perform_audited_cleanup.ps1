$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
if ($taskRoot -ne 'C:\Users\smile\Desktop\test2\mixure_test_SAM') { throw 'Unexpected workspace' }
$cleanupRoot = Join-Path $taskRoot 'outputs\current_development\cleanup'
$dry = Get-Content -LiteralPath (Join-Path $cleanupRoot 'dry_run.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $dry.dry_run_passed) { throw 'Dry-run gate has not passed' }
$before = Get-Content -LiteralPath (Join-Path $cleanupRoot 'CLEANUP_MANIFEST_BEFORE.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$records = [Collections.Generic.List[object]]::new()
foreach ($entry in $before.delete) {
    $target = [IO.Path]::GetFullPath((Join-Path $taskRoot $entry.path))
    if (-not $target.StartsWith($taskRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Deletion outside workspace' }
    if ($entry.path -match '^(outputs_v292|outputs_v293)[/\\][^.]' -or $entry.path -match '(?i)validation|held.?out' -or $target -match '(?i)\.(mp4|mov|avi|mkv)$') { throw 'Protected target' }
    $result = [ordered]@{path=$entry.path; bytes=$entry.size; files=$entry.files; directories=$entry.directories; deleted=$false; error=$null}
    try {
        if (Test-Path -LiteralPath $target) {
            $resolved = (Resolve-Path -LiteralPath $target).ProviderPath
            if (-not $resolved.StartsWith($taskRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Resolved deletion outside workspace' }
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
        $result.deleted = -not (Test-Path -LiteralPath $target)
    } catch { $result.error = $_.Exception.Message }
    $records.Add([pscustomobject]$result)
    Write-Output ('Cleanup ' + $entry.path + ' deleted=' + $result.deleted)
}
$after = [ordered]@{
    schema='audited_cleanup_1'; manifest_before_sha256=(Get-FileHash -LiteralPath (Join-Path $cleanupRoot 'CLEANUP_MANIFEST_BEFORE.json') -Algorithm SHA256).Hash.ToLower()
    deletion_utc=[DateTime]::UtcNow.ToString('o'); records=$records; raw_data_deleted=$false; validation_accessed=$false
    known_reclaimed_bytes=($records | Where-Object deleted | Measure-Object bytes -Sum).Sum
    known_deleted_files=($records | Where-Object deleted | Measure-Object files -Sum).Sum
    known_deleted_directories=($records | Where-Object deleted | Measure-Object directories -Sum).Sum
    failures=@($records | Where-Object { -not $_.deleted })
}
$after | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $cleanupRoot 'CLEANUP_MANIFEST_AFTER.json') -Encoding UTF8
