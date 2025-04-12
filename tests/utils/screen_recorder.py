"""
Screen recorder utility for capturing test execution.

This module provides a screen recorder class that can be used to record
the screen during test execution, making it easier to debug and review tests.
"""

import os
import time
import datetime
import threading
import cv2
import numpy as np
import pyautogui
from pathlib import Path


class ScreenRecorder:
    """
    A class for recording the screen during test execution.
    
    This class uses OpenCV and PyAutoGUI to capture and record the screen.
    It runs in a separate thread to avoid blocking the test execution.
    """
    
    def __init__(self, output_dir="test_recordings", fps=10, codec="XVID"):
        """
        Initialize the screen recorder.
        
        Args:
            output_dir (str): Directory where recordings will be saved
            fps (int): Frames per second for the recording
            codec (str): Four character code for the video codec (e.g., "XVID", "MP4V")
        """
        self.output_dir = output_dir
        self.fps = fps
        self.codec = codec
        self.recording = False
        self.thread = None
        self.out = None
        
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    def start_recording(self, test_name=None):
        """
        Start recording the screen.
        
        Args:
            test_name (str, optional): Name of the test being recorded.
                If not provided, a timestamp will be used.
        
        Returns:
            str: Path to the output video file
        """
        if self.recording:
            print("Recording is already in progress")
            return
        
        # Generate output file name
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if test_name:
            # Replace spaces and special characters with underscores
            test_name = "".join(c if c.isalnum() else "_" for c in test_name)
            filename = f"{test_name}_{timestamp}.avi"
        else:
            filename = f"recording_{timestamp}.avi"
        
        self.output_file = os.path.join(self.output_dir, filename)
        
        # Get screen size
        screen_size = pyautogui.size()
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*self.codec)
        self.out = cv2.VideoWriter(
            self.output_file, 
            fourcc, 
            self.fps, 
            (screen_size.width, screen_size.height)
        )
        
        # Start recording in a separate thread
        self.recording = True
        self.thread = threading.Thread(target=self._record)
        self.thread.daemon = True
        self.thread.start()
        
        print(f"Started recording to {self.output_file}")
        return self.output_file
    
    def stop_recording(self):
        """
        Stop the recording.
        
        Returns:
            str: Path to the output video file
        """
        if not self.recording:
            print("No recording in progress")
            return None
        
        self.recording = False
        if self.thread:
            self.thread.join(timeout=5)
        
        if self.out:
            self.out.release()
        
        print(f"Stopped recording. Video saved to {self.output_file}")
        return self.output_file
    
    def _record(self):
        """
        Internal method to record the screen.
        This runs in a separate thread.
        """
        try:
            while self.recording:
                # Capture the screen
                img = pyautogui.screenshot()
                
                # Convert the image to a numpy array
                frame = np.array(img)
                
                # Convert from BGR to RGB (PyAutoGUI uses RGB, OpenCV uses BGR)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Write the frame to the video file
                self.out.write(frame)
                
                # Sleep to achieve the desired frame rate
                time.sleep(1 / self.fps)
        except Exception as e:
            print(f"Error during recording: {e}")
            self.recording = False
            if self.out:
                self.out.release()


# Example usage
if __name__ == "__main__":
    # Create a recorder instance
    recorder = ScreenRecorder()
    
    # Start recording
    recorder.start_recording("example_test")
    
    # Simulate test execution
    print("Running test...")
    time.sleep(5)
    
    # Stop recording
    recorder.stop_recording()
    
    print("Done!")
