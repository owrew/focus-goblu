$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
New-Item -ItemType Directory -Force models | Out-Null
Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-tiny.cfg' -OutFile 'models\yolov4-tiny.cfg'
Invoke-WebRequest -Uri 'https://github.com/AlexeyAB/darknet/releases/download/yolov4/yolov4-tiny.weights' -OutFile 'models\yolov4-tiny.weights'
Get-FileHash 'models\yolov4-tiny.weights' -Algorithm SHA256
Write-Host 'Select models\yolov4-tiny.weights in Control room, save settings, then restart monitoring.'
