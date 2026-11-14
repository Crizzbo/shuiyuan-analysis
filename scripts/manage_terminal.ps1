# PowerShell 统一包装脚本：水源分析终端进程管理中枢
param (
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action,

    [int]$Port = 8765,
    [string]$HostAddress = "127.0.0.1",
    [switch]$Open,
    [switch]$ManualOnly
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$PythonScript = Join-Path $ScriptDir "manage_terminal.py"

$ArgsList = @($PythonScript, $Action, "--port", $Port, "--host", $HostAddress)
if ($Open) {
    $ArgsList += "--open"
}
if ($ManualOnly) {
    $ArgsList += "--manual-only"
}

python @ArgsList
exit $LASTEXITCODE
