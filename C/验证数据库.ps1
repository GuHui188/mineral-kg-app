$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$runtimePython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $runtimePython)) { $runtimePython = (Get-Command python -ErrorAction Stop).Source }
$env:PYTHONIOENCODING = 'utf-8'
$env:NEO4J_HTTP_URL = 'http://127.0.0.1:7474'
$env:NEO4J_DATABASE = 'neo4j'
$env:NEO4J_USER = 'neo4j'
$securePassword = Read-Host 'Neo4j password (local session only)' -AsSecureString
try {
    $env:NEO4J_PASSWORD = [System.Net.NetworkCredential]::new('', $securePassword).Password
    & $runtimePython (Join-Path $PSScriptRoot 'verify_neo4j.py')
    $verificationExit = $LASTEXITCODE
    if ($verificationExit -ne 0) { throw 'Verification failed. Read reports/neo4j_verification.json.' }
} finally {
    Remove-Item Env:\NEO4J_PASSWORD -ErrorAction SilentlyContinue
    $securePassword = $null
}
