# Recommended phone detector

OpenCV Zoo YOLOX-S COCO, downloaded 2026-11-03:
https://huggingface.co/opencv/object_detection_yolox/resolve/main/object_detection_yolox_2022nov.onnx

Saved locally as phone-yolox.onnx, 35,858,002 bytes.
SHA256: c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063

Model documentation / preprocessing reference:
https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_yolox

The upstream Apache 2.0 license is included as YOLOX-LICENSE.txt. This is an unmodified pretrained general object model, not trained on the user's camera or phone. The app filters COCO class 67. Model files remain external dependencies under upstream terms. Runtime is local and does not download models.

COCO128 phone-labelled images were used only for development sanity checks. They are not distributed with the application/source archives and do not establish real-world accuracy.
