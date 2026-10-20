$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\Users\smile\Desktop\test2\mixure_test_SAM'
# Wait only for this experiment's Qwen process, never launch two heavy models.
do {
    $ownedQwen = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { $_.CommandLine -like '*scripts/run_three_vlm_dataset.py qwen*' })
    if ($ownedQwen.Count -gt 0) { Start-Sleep -Seconds 10 }
} while ($ownedQwen.Count -gt 0)
$experimentRoot = 'artifacts/pass_t/phase3/three_vlm_full_v1'
$expectedCalls = (Get-Content -LiteralPath "$experimentRoot/dataset_freeze.json" -Raw | ConvertFrom-Json).unique_inputs
function Assert-TerminalCalls([string]$modelName) {
    $modelRoot = "$experimentRoot/runs/$modelName"
    $terminalCalls = @(Get-ChildItem -LiteralPath $modelRoot -Directory | Where-Object { (Test-Path -LiteralPath (Join-Path $_.FullName 'receipt.json')) -or (Test-Path -LiteralPath (Join-Path $_.FullName 'failure.json')) })
    if ($terminalCalls.Count -ne $expectedCalls) { throw "Incomplete $modelName calls: $($terminalCalls.Count)/$expectedCalls" }
}
Assert-TerminalCalls 'qwen'
$ErrorActionPreference = 'Continue'
& .venv\Scripts\python.exe -X utf8 -B scripts/run_three_vlm_dataset.py videollama *> "$experimentRoot/videollama_run_02.log"
$modelExitCode = $LASTEXITCODE
$ErrorActionPreference = 'Stop'
if ($modelExitCode -ne 0) { throw 'VideoLLaMA process failed; preserve outputs and repair unfinished integration.' }
Assert-TerminalCalls 'videollama'
Start-Sleep -Seconds 2
$ErrorActionPreference = 'Continue'
& wsl.exe -d Ubuntu -- bash -lc 'cd /mnt/c/Users/smile/Desktop/test2/mixure_test_SAM; export PYTHONPATH="$PWD/.runtime/nemotron/sitepackages_linux"; export VLLM_NO_USAGE_STATS=1; export DO_NOT_TRACK=1; python3 -B scripts/run_nemotron_full.py' *> "$experimentRoot/nemotron_run_01.log"
$modelExitCode = $LASTEXITCODE
$ErrorActionPreference = 'Stop'
if ($modelExitCode -ne 0) { throw 'Nemotron process failed; inspect preserved engineering evidence.' }
