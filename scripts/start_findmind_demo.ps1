param([int]$Port = 8514,[int]$MaxUploadMB = 200)
$repoPath = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = "$repoPath\artifacts\pass_i\runtime\vendor;$repoPath\src"
$env:FINDMIND_UPLOAD_MAX_MB = "$MaxUploadMB"
$demoTempPath = Join-Path $repoPath '.runtime\findmind_demo\temp'
New-Item -ItemType Directory -Force -Path $demoTempPath | Out-Null
$env:TEMP = $demoTempPath
$env:TMP = $demoTempPath
Set-Location -LiteralPath $repoPath
& "$repoPath\.venv\Scripts\python.exe" -X utf8 -B -m streamlit run "$repoPath\apps\findmind_demo.py" --global.developmentMode false --server.address 127.0.0.1 --server.port $Port --server.maxUploadSize $MaxUploadMB --server.fileWatcherType none --browser.gatherUsageStats false --server.headless true --server.enableCORS true --theme.base light --theme.primaryColor '#1d7463' --theme.backgroundColor '#ffffff' --theme.secondaryBackgroundColor '#f3f6f7' --theme.textColor '#203331' --logger.level warning
