import cv2
import threading
import time

class VideoSource:
    def __init__(self, filepath: str, max_size: int = 1280, loop: bool = True):
        self.filepath = filepath
        self.cap = cv2.VideoCapture(filepath)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.current_frame = None  # RGB frame
        self.playing = True
        self.loop = loop
        self.finished = False
        self.lock = threading.Lock()
        self.max_size = max_size

    def _resize_frame(self, frame):
        h, w = frame.shape[:2]
        if w <= self.max_size and h <= self.max_size:
            return frame
        scale = self.max_size / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    def read_frame(self):
        """Decode next frame; called from background thread."""
        with self.lock:
            if not (self.cap and self.cap.isOpened()):
                return self.current_frame
            
            if not self.playing or self.finished:
                return self.current_frame

            ret, frame = self.cap.read()
            if ret:
                frame = self._resize_frame(frame)
                self.current_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                if self.loop:
                    # Loop video
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    # Read the first frame immediately to avoid a black flash or stall
                    ret, frame = self.cap.read()
                    if ret:
                        frame = self._resize_frame(frame)
                        self.current_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                else:
                    self.finished = True
                    self.playing = False
                    
        return self.current_frame

    def get_current_frame(self):
        with self.lock:
            return self.current_frame

    def play(self):
        with self.lock:
            self.playing = True
            if self.finished:
                self.finished = False
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def pause(self):
        with self.lock:
            self.playing = False

    def stop(self):
        with self.lock:
            self.playing = False
            self.finished = False
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            # Optionally clear current frame or keep last one? Keeping last one is usually better for UI.

    def is_finished(self):
        with self.lock:
            return self.finished

    def release(self):
        with self.lock:
            if self.cap:
                self.cap.release()
                self.cap = None
