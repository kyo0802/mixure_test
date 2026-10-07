param([int]$Port = 8511)
$repoPath = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = "$repoPath\artifacts\pass_i\runtime\vendor;$repoPath\src"
& "$repoPath\.venv\Scripts\python.exe" -m streamlit run "$PSScriptRoot\pass_i_annotation_app.py" --global.developmentMode false --server.address 127.0.0.1 --server.port $Port --server.fileWatcherType poll --browser.gatherUsageStats false --server.headless true
