import logging
import torch
from ..config import DetectorConfig
from ..models import Detection, FrameInfo
from .runtime import configure_ultralytics

logger = logging.getLogger(__name__)


class Detector:
    def __init__(self, config: DetectorConfig):
        # Keep Ultralytics settings local and disable its implicit package installer.
        configure_ultralytics()
        from ultralytics import YOLO
        self.config = config
        torch.set_num_threads(config.cpu_threads)
        self.device = ("0" if torch.cuda.is_available() else "cpu") if config.device == "auto" else config.device
        self.model = YOLO(config.model)
        self.names = self.model.names
        logger.info("Detector %s; device=%s; torch=%s; CUDA=%s", config.model, self.device,
                    torch.__version__, torch.cuda.is_available())

    def detect(self, frame, info: FrameInfo) -> list[Detection]:
        result = self.model.predict(frame, conf=self.config.confidence, imgsz=self.config.image_size,
                                    device=self.device, verbose=False)[0]
        detections = []
        if result.boxes is not None:
            for row in result.boxes.cpu().numpy().data:
                x1, y1, x2, y2, confidence, class_id = row[:6]
                if x2 > x1 and y2 > y1:
                    detections.append(Detection(class_id=int(class_id), class_name=self.names[int(class_id)],
                        confidence=float(confidence), bbox=tuple(float(x) for x in (x1, y1, x2, y2)),
                        frame_index=info.frame_index, timestamp=info.timestamp))
        return detections
