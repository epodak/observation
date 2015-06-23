#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 23.06.2015

@author: kolbe
'''
import os, time, sys
from datetime import datetime
sys.path.insert(1,'..')
import pygtk
pygtk.require('2.0')
import gtk
import webkit
import cv2
from picamera.array import PiRGBArray
from picamera import PiCamera
import picamera
from sensors import hcsr04
from threading import Thread
from jinja2 import Template


DISTANCE_TRIGGER = 18
DISTANCE_ECHO = 24
MIN_DISTANCE = 1.0

class Application():
    
    def __init__(self):
        # create mainwindow
        self.window = gtk.Window()
        self.window.set_title("iDENT")
        # create widgets
        self.createWidgets()
        # connect event handlers
        self.connectSignals()
        # show start widget
        self.showStartWidget()
        # show all in fullscreen
        self.window.show_all()
        self.window.fullscreen()
        
        # init current image/dir data
        self.current_dir = None
        # init camera
        #self.initCamera()
        self.video_active = False
        # init ultrasonic distance sensor
        self.initHCSR04()
        # start measure thread
        self.measure_thread_run = False
        self.measure_thread = Thread(target=self.measureDistance)
        self.measure_thread.start()
        
        #start main loop
        gtk.main()
        
    def initCamera(self):
        self.camera = PiCamera()
        self.camera.vflip = False
        self.camera.hflip = False
        self.camera.resolution = (640, 480)
    
        # allow the camera to warmup
        time.sleep(0.1)
        
        # capture initial frame
        rawCapture = PiRGBArray(self.camera)
        self.camera.capture(rawCapture, format="bgr")
        image = rawCapture.array
        
    def initHCSR04(self):
        self.hcsr04 = hcsr04.HCSR04(DISTANCE_TRIGGER, DISTANCE_ECHO)
        
    def measureDistance(self):
        self.measure_thread_run = True
        with self.hcsr04 as d:
            while self.measure_thread_run:
                distance = d.average_distance(5)
                print distance
                if self.notebook.current_page() == 0 and distance <= MIN_DISTANCE:
                    image = self.takePhoto()
                    self.current_dir = self.createNewDirectory()
                    cv2.imwrite(os.path.join(self.current_dir, "image.jpg"), image)
                    self.showQuestionWidget()
                elif self.notebook.current_page() == 2 and not self.video_active:
                    distance = d.average_distance(10)
                    if distance > MIN_DISTANCE:
                        self.showStartWidget()
                time.sleep(0.2)
        
    def createWidgets(self):
        self.notebook = gtk.Notebook()
        self.notebook.set_show_tabs(False)
        
        # set start page
        self.start_label = gtk.Label("Startseite")
        # set question page
        self.question = gtk.VBox(spacing=10)
        self.button_yes = gtk.Button("JA", stock=gtk.STOCK_YES)
        self.button_no = gtk.Button("NEIN", stock=gtk.STOCK_NO)
        self.question_label = gtk.Label("Möchten Sie das Bild wirklich hochladen?")
        self.question_image = gtk.Image()
        self.question.pack_start(self.question_label)
        self.question.pack_start(self.question_image)
        self.question.pack_start(self.button_yes)
        self.question.pack_start(self.button_no)
        # set webview
        self.web = webkit.WebView()
        # append to notebook
        self.notebook.append_page(self.start_label)
        self.notebook.append_page(self.question)
        self.notebook.append_page(self.web)
        self.notebook.show()
        # append to mainwindow
        self.window.add(self.notebook)
        
    def connectSignals(self):
        self.button_yes.connect("clicked", self.callback_yes_no)
        self.button_no.connect("clicked", self.callback_yes_no)
        self.window.connect("key-press-event", self.on_key)
        self.window.connect("destroy", gtk.main_quit)
        
    def on_key(self, widget, event):
        # ESC
        if event.keyval == 65307:
            self.exit()
        
        
    def callback_yes_no(self, widget, callback_data=None):
        self.showWebWidget()

    def showStartWidget(self):
        self.notebook.set_current_page(0)
        
    def showQuestionWidget(self):
        self.question_image.set_from_file(os.path.join(self.current_dir, "image.jpg"))
        self.notebook.set_current_page(1)

    def showWebWidget(self):
        html = self.renderHTML()
        html_file = self.saveHTML(html)
        self.web.open(html_file)
        self.notebook.set_current_page(2)
        Thread(target=self.takeVideo, args=(self.current_dir, 10)).start()
        #self.notebook.set_current_page(0)
        
    def takePhoto(self):
        with picamera.PiCamera() as cam:
            cam.resolution = (640, 480)
            rawCapture = PiRGBArray(cam)
            cam.capture(rawCapture, format="rgb")
            image = rawCapture.array
        return image
    
    def takeVideo(self, directory, length=10):
        self.video_active = True
        with picamera.PiCamera() as cam:
            cam.resolution = (640, 480)
            cam.start_recording(os.path.join(directory, 'video.h264'))
            cam.wait_recording(length)
            cam.stop_recording()
        self.video_active = False
    
    def createNewDirectory(self):
        now = datetime.now()
        dir_name = now.strftime("%Y-%m-%d_%H-%M-%S")
        os.mkdir(dir_name)
        return dir_name
    
    def renderHTML(self):
        with open( os.path.dirname(os.path.abspath(__file__))+"/template/template.html", 'r') as r:
            template = Template(r.read())
        return template.render()
    
    def saveHTML(self, html):
        html_file = os.path.join(self.current_dir, "index.html")
        with open(html_file, 'w') as f:
            f.write(html)  
        return os.path.abspath(html_file)
    
    def exit(self):
        self.measure_thread_run = False
        self.measure_thread.join()
        self.window.destroy()
        
        

if __name__ == '__main__':
    app = Application()