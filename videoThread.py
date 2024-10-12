import os
import pandas as pd
import csv
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtMultimedia import *
from PySide6.QtMultimediaWidgets import *
from pyqtgraph import PlotWidget, plot
from config import speed_list
import pyqtgraph as pg
import math
import sys
import cv2
import time


class GifState():
    """Stores time and pixel map together
    """
    def __init__(self, pixmap, time):
        self.pixmap = pixmap
        self.time = time


class VideoThread(QThread):
    """Displays the video and interfaces with controls
    """
    change_pixmap_signal = Signal(GifState)
    pause_video_received = Signal()
    resume_video_received = Signal()

    def __init__(self, input_frame, seconds_before_loop, cap, playback_rate):
        super().__init__()
        self._run_flag = True
        self.input_frame = input_frame
        self.latest_input_frame = input_frame
        self.cap = cap
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, input_frame)
        self.playback_rate = playback_rate
        self.seconds_before_loop = seconds_before_loop
        self.time_since_last_frame = time.time()
        self.pause_pressed = False
        self.reset_flag = False
        self.speed_ratio = 1
        print("loop time: " + str(seconds_before_loop))
        print("input frame: " +  str(self.input_frame))
        print("playback_rate: " + str(self.playback_rate))
        print("Actual fps: " + str(cv2.CAP_PROP_FPS))
        print("Actual fps pt 2: " + str(self.cap.get(cv2.CAP_PROP_FPS)))

    def pause_video_received(self):
        """Pause video playback
        """
        self.pause_pressed = True

    def resume_video_received(self):
        """Resume video playback
        """
        self.pause_pressed = False

    def reset_gif(self):
        """Reset back to red line
        """
        self.reset_flag = True

    def num_changed(self, index):
        self.speed_ratio = speed_list[index]
        

    def run(self):
        """Run through video 
        """
        frame_begin_time = time.perf_counter()
        count = 0
        print("Initializing image...")
        ret, frame = self.cap.read() # takes time, calling grab instead of read will allow us to move forward in the frame method
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = frame.shape
            img = QImage(frame, width, height, QImage.Format_RGB888)
            pix = QPixmap.fromImage(img)

        
        frames_before_loop = self.seconds_before_loop * self.cap.get(cv2.CAP_PROP_FPS)
        
        # How many fames have passed in any given amount of time
        frames_since_begin = (self.cap.get(cv2.CAP_PROP_POS_FRAMES) - self.input_frame)

        count=0
        while self._run_flag:
            num_frames_to_skip = max(0,  math.ceil((((self.cap.get(cv2.CAP_PROP_FPS) * (self.speed_ratio))) / (self.playback_rate)) - 1))
            
            if(self.input_frame != self.latest_input_frame): # Logic for if the red line is moved

                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.input_frame)

            self.latest_input_frame = self.input_frame
            if(self.pause_pressed):
                continue
                
            # if(time.time() - self.time_since_last_frame) < ((1.0/self.cap.get(cv2.CAP_PROP_FPS) * (1.0/self.speed_ratio))):
            #     continue
            count+=1
            if(time.time() - self.time_since_last_frame) > (((num_frames_to_skip+1.0)/self.cap.get(cv2.CAP_PROP_FPS) * (1.0/self.speed_ratio))):
                print(count)
                count=0
                # if count % math.ceil(((self.cap.get(cv2.CAP_PROP_FPS) * (self.speed_ratio))) / (self.playback_rate)) > 0:
                #     self.cap.grab()
                #     continue

                # print(f"Num frames to skip: {num_frames_to_skip}")
                print(time.time() - self.time_since_last_frame)

                #count+=1
                self.time_since_last_frame = time.time()
                # if count <= num_frames_to_skip:
                #     self.cap.grab()
                #     continue

                #count = 0
                self.change_pixmap_signal.emit(GifState(pix, frames_since_begin / self.cap.get(cv2.CAP_PROP_FPS)))
                ret, frame = self.cap.read() # takes time, calling grab instead of read will allow us to move forward in the frame method
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    height, width, channel = frame.shape
                    img = QImage(frame, width, height, QImage.Format_RGB888)
                    pix = QPixmap.fromImage(img)

                
                frames_before_loop = self.seconds_before_loop * self.cap.get(cv2.CAP_PROP_FPS)
                
                # How many fames have passed in any given amount of time
                frames_since_begin = (self.cap.get(cv2.CAP_PROP_POS_FRAMES) - self.input_frame)
                
                for _ in range(num_frames_to_skip):
                    self.cap.grab()

                # If goes past gif alloted time
                if ((frames_since_begin > frames_before_loop) # goes past gif time 
                or (frames_since_begin < 0) # move line backwards
                or (self.reset_flag) #user resets
                or ((self.cap.get(cv2.CAP_PROP_POS_FRAMES) == self.cap.get(cv2.CAP_PROP_FRAME_COUNT)))): # goes past time count
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.input_frame)
                    print(f"frames_before_loop:{frames_before_loop}")
                    self.curr_frame = self.input_frame
                    frames_since_begin = 0
                    self.reset_flag = False
                    last_reset_time = time.time()
                #update image
            
            

    def stop(self):
        """Stop the video playback on application termination
        """
        self._run_flag = False
        self.wait()