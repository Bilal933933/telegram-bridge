param([ValidateSet('start', 'stop', 'status', 'restart')][string]$Action = 'status')

$ErrorActionPreference = 'Stop'
$Base = $PSScriptRoot
$PidFile = Join-Path $Base 'bridge.pid'
$LogFile = Join-Path $Base 'bridge.log'
$Script = Join-Path $Base 'bot.py'

function Get-Running {
    if (-not (Test-Path $PidFile)) { return $null }
    $procId = [int]((Get-Content $PidFile -Raw).Trim())
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc -and $proc.ProcessName -match 'python') { return $proc }
    return $null
}

switch ($Action) {
    'start' {
        $running = Get-Running
        if ($running) { "already running (PID $($running.Id))"; break }
        $proc = Start-Process -FilePath 'python' -ArgumentList @($Script) -WorkingDirectory $Base `
            -WindowStyle Hidden -PassThru -RedirectStandardOutput $LogFile -RedirectStandardError "$LogFile.err"
        $proc.Id | Set-Content $PidFile -Encoding ascii
        Start-Sleep -Seconds 2
        if (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue) {
            "started (PID $($proc.Id))"
        } else {
            "failed to start - check $LogFile and $LogFile.err"
        }
    }
    'stop' {
        $running = Get-Running
        if (-not $running) { "not running"; Remove-Item $PidFile -ErrorAction SilentlyContinue; break }
        Stop-Process -Id $running.Id -Force
        Remove-Item $PidFile -ErrorAction SilentlyContinue
        "stopped (PID $($running.Id))"
    }
    'restart' {
        & $PSCommandPath stop
        Start-Sleep -Seconds 1
        & $PSCommandPath start
    }
    'status' {
        $running = Get-Running
        if ($running) { "running (PID $($running.Id))" } else { "stopped" }
    }
}


