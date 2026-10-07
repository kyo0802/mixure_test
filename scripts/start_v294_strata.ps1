$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskTools = Join-Path $taskRoot 'tools\Strata'
$taskPython = Join-Path $taskTools '.venv\Scripts\python.exe'
$taskConfig = Join-Path $taskTools 'strata-coder-iq1_m.json'
$taskOutput = Join-Path $taskRoot 'outputs\v294_qwen38\setup'
if (-not (Test-Path -LiteralPath $taskConfig)) { throw 'Official Strata setup must finish first.' }
$taskConfiguration = Get-Content -LiteralPath $taskConfig -Raw | ConvertFrom-Json
if ($taskConfiguration.host -ne '127.0.0.1') { throw 'V294 requires loopback-only configuration.' }
$env:APPDATA = Join-Path $taskTools 'config-state'
$env:TEMP = Join-Path $taskTools 'temp'
$env:TMP = $env:TEMP
$env:HF_HOME = Join-Path $taskRoot 'tools\Strata-data\hf'
$env:PIP_CACHE_DIR = Join-Path $taskTools 'pip-cache'
Remove-Item Env:STRATA_DEBUG -ErrorAction SilentlyContinue
$taskStamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$taskArguments = @('-X','utf8','-B',('"'+(Join-Path $taskTools 'serve\server.py')+'"'),
    '--engine','strata','--config',('"'+$taskConfig+'"'),'--host','127.0.0.1','--port','8080')
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList $taskArguments -WorkingDirectory $taskTools -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $taskOutput "server_stdout_$taskStamp.log") `
    -RedirectStandardError (Join-Path $taskOutput "server_stderr_$taskStamp.log")
@{pid=$taskProcess.Id;started=(Get-Date).ToString('o');python=$taskPython;arguments=$taskArguments;
    stdout="server_stdout_$taskStamp.log";stderr="server_stderr_$taskStamp.log";config=$taskConfig} |
    ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $taskOutput 'server_process.json') -Encoding utf8
Write-Output "Strata starting on 127.0.0.1:8080; PID $($taskProcess.Id)."
