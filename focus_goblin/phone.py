"""YOLOv4-tiny COCO via OpenCV DNN; no PyTorch required."""
from pathlib import Path


class TinyPhoneDetector:
    def __init__(self, weights, confidence=.5):
        import cv2
        config = Path(weights).with_suffix('.cfg')
        if not config.is_file():
            raise FileNotFoundError('YOLOv4-tiny needs its matching .cfg beside the .weights file')
        self.net = cv2.dnn.readNetFromDarknet(str(config),str(weights))
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.layers = self.net.getUnconnectedOutLayersNames()
        self.confidence = confidence

    def predict_phone(self, frame):
        import cv2
        blob = cv2.dnn.blobFromImage(frame,1/255.,(320,320),swapRB=True,crop=False)
        self.net.setInput(blob)
        for output in self.net.forward(self.layers):
            for detection in output:
                # COCO zero-based 67 = cell phone. Both objectness and class probability matter.
                if len(detection) >= 85 and float(detection[4]*detection[5+67]) >= self.confidence:
                    return True
        return False
