$ErrorActionPreference='Stop'
$taskRoot='C:\Users\smile\Desktop\test2\mixure_test_SAM'
$clean=Join-Path $taskRoot 'outputs\current_development\cleanup'
$after=Get-Content -LiteralPath (Join-Path $clean 'CLEANUP_MANIFEST_AFTER.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$extra=@()
foreach ($name in @('test_v241_generalization.py','test_v261_ablation.py')) {
    $rel='tests/'+$name
    $p=Join-Path $taskRoot $rel
    $extra+=@{path=$rel;size=(Get-Item -LiteralPath $p).Length;files=1;directories=0;reason='Output-only fixtures of removed experiments; no operational tests or source dependencies; historical hash failures removed with scope, not repaired'}
}
@{delete=$extra;validation_not_accessed=$true} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $clean 'CLEANUP_MANIFEST_SUPPLEMENT.json') -Encoding UTF8
$records=@($after.records)
foreach ($entry in (@($after.failures)+$extra)) {
    $target=[IO.Path]::GetFullPath((Join-Path $taskRoot $entry.path))
    if (-not $target.StartsWith($taskRoot+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Outside workspace'}
    if (Test-Path -LiteralPath $target) {
        $resolved=(Resolve-Path -LiteralPath $target).ProviderPath
        if (-not $resolved.StartsWith($taskRoot+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Outside resolved workspace'}
        Remove-Item -LiteralPath $resolved -Force -Recurse
    }
    if ($entry.PSObject.Properties.Name -contains 'deleted') {$entry.deleted=$true;$entry.error=$null}
    else {$records+= [pscustomobject]@{path=$entry.path;bytes=$entry.size;files=1;directories=0;deleted=$true;error=$null}}
    Write-Output ('Completed cleanup '+$entry.path)
}
$after.records=$records
$after.failures=@($records|Where-Object {-not $_.deleted})
$after.known_reclaimed_bytes=($records|Where-Object deleted|Measure-Object bytes -Sum).Sum
$after.known_deleted_files=($records|Where-Object deleted|Measure-Object files -Sum).Sum
$after.known_deleted_directories=($records|Where-Object deleted|Measure-Object directories -Sum).Sum
$after|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $clean 'CLEANUP_MANIFEST_AFTER.json') -Encoding UTF8
