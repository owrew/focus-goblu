$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
New-Item -ItemType Directory -Force models | Out-Null
Invoke-WebRequest -Uri 'https://huggingface.co/opencv/object_detection_yolox/resolve/main/object_detection_yolox_2022nov.onnx' -OutFile 'models\phone-yolox.onnx'
Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/object_detection_yolox/LICENSE' -OutFile 'models\YOLOX-LICENSE.txt'
Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-tiny.cfg' -OutFile 'models\yolov4-tiny.cfg'
Invoke-WebRequest -Uri 'https://github.com/AlexeyAB/darknet/releases/download/yolov4/yolov4-tiny.weights' -OutFile 'models\yolov4-tiny.weights'
Get-FileHash 'models\yolov4-tiny.weights' -Algorithm SHA256
Write-Host 'Balanced YOLOX is now auto-discovered. Restart the camera. Eco YOLOv4 remains available in Settings.'
