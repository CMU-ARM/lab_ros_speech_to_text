#!/usr/bin/python3

import sys
import time
import getopt
import alsaaudio
from google.cloud import speech
from lab_ros_speech_to_text.msg import Speech as Speech_msg
import io
import rospy
import threading

#We create an audio lick object here
class audioStreamingObject():

    def __init__(self):
        self._inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NONBLOCK)
        self._inp.setchannels(1)
        self._inp.setrate(16000)
        self._inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        self._inp.setperiodsize(80)
        self.closed = False

    def read(self, size):

        if self.closed:
            return None

        cur_l, cur_data = self._inp.read()
        while(cur_l < size):
            time.sleep(.001)
            l, data = self._inp.read()
            cur_l += l
            cur_data += data
        #print("returning data:{}".format(cur_l))
        return cur_data

    def close(self):
        self.closed = True

def close_loop(stream):
    for i in range(0,60):
        time.sleep(1)
        if rospy.is_shutdown():
            break
    stream.close()

def main():

    rospy.init_node('stt_node')
    pub = rospy.Publisher('stt', Speech_msg, queue_size=10)
    while not rospy.is_shutdown():
        #restart the client and sample
        stream = audioStreamingObject()
        #print(stream.closed)
        rospy.loginfo("starting stream audio to Google")
        #close thread
        close_thread = threading.Thread(target=close_loop, args=(stream,))
        close_thread.start()
        client = speech.Client()
        sample = client.sample(stream=stream,
            encoding=speech.Encoding.LINEAR16,
            sample_rate_hertz=16000)
        results = sample.streaming_recognize(
            language_code='en-US',
            interim_results=True
        )
        for result in results:
            for alternative in result.alternatives:
                msg = Speech_msg()
                msg.text = str(alternative.transcript)
                if alternative.confidence is not None:
                    msg.confidence = float(alternative.confidence)
                else:
                    msg.confidence = 0
                msg.is_final = result.is_final
                pub.publish(msg)
        
        if not rospy.is_shutdown():
            rospy.loginfo("restarting google speech api due to time limit")
    rospy.loginfo('STT main thread stopping')

if __name__ == '__main__':
    main()