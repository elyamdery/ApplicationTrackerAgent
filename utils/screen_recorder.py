"""
Screen Recorder Utility
Automates screen recording for tests.
"""

import cv2
import numpy as np
import pyautogui
import threading

class ScreenRecorder:
    def __init__(self, output_file='screen_recording.avi', fps=10):
        self.output_file = output_file
        self.fps = fps
        self.recording = False
        self.thread = None

    def start_recording(self):
        self.recording = True
        self.thread = threading.Thread(target=self._record)
        self.thread.start()

    def stop_recording(self):
        self.recording = False
        if self.thread:
            self.thread.join()

    def _record(self):
        screen_size = pyautogui.size()
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter(self.output_file, fourcc, self.fps, screen_size)

        while self.recording:
            img = pyautogui.screenshot()
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            out.write(frame)

        out.release()