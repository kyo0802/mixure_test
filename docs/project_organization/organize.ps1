$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
if ($repo -ne 'C:\Users\smile\Desktop\test2\mixure_test_SAM') { throw 'Unexpected repository' }
$baseline = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'before.json') -Raw | ConvertFrom-Json
$journalPath = Join-Path $PSScriptRoot 'move_journal.json'
if (Test-Path -LiteralPath $journalPath) { throw 'Existing journal: inspect before resuming' }
$journal = @()
foreach ($move in $baseline.moves) {
    $source = [IO.Path]::GetFullPath((Join-Path $repo $move.old))
    $destination = [IO.Path]::GetFullPath((Join-Path $repo $move.new))
    foreach ($p in @($source, $destination)) {
        if (-not $p.StartsWith($repo + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Out of workspace' }
    }
    if (Test-Path -LiteralPath $destination) { throw "Destination exists: $destination" }
    $original = Get-Item -LiteralPath $source -Force
    if ($original.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Source already linked' }
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Move-Item -LiteralPath $source -Destination $destination
    try {
        New-Item -ItemType Junction -Path $source -Target $destination | Out-Null
        $current = (& git -C $repo status --porcelain --untracked-files=no) -join "`n"
        if ($current.TrimEnd() -ne $baseline.git_tracked_status.TrimEnd()) { throw 'Tracked Git status changed through junction' }
    } catch {
        if ((Test-Path -LiteralPath $source) -and ((Get-Item -LiteralPath $source -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            # Nonrecursive unlink of this newly created junction only.
            [IO.Directory]::Delete($source)
        }
        Move-Item -LiteralPath $destination -Destination $source
        throw
    }
    $journal += @{old=$move.old;new=$move.new;files=$move.files;bytes=$move.bytes;original_attributes=[int]$original.Attributes}
    $journal | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $journalPath -Encoding utf8
    Write-Output "Archived $($move.old) -> $($move.new)"
}
