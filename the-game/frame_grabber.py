import cv2
import threading
import queue
import time


class FrameGrabber:
    def __init__(self, url):
        self.url = url
        self.queue = queue.Queue(maxsize=1)  # keep only newest frame
        self.thread = threading.Thread(target=self.run_thread, daemon=True)

    def start(self):
        self.thread.start()

    def pop_frame(self):
        return self.queue.get()

    def push_frame(self, frame):
        try:
            self.queue.get_nowait()
        except queue.Empty:
            pass
        self.queue.put_nowait(frame)

    def run_thread(self):
        print(f"Frame grabber started")
        while True:
            try:
                cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
                if not cap.isOpened():
                    raise Exception(f"Could not open RTSP: {self.url}")

                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # no buffering

                while True:
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        raise Exception(f"Bad frame")

                    self.push_frame(frame)

            except Exception as e:
                print(f"FRAME ERROR: {e}")
                time.sleep(1)
                raise
