#!/usr/bin/python

import serial
import signal
import httplib
import threading
import binascii
from datetime import datetime
from base64 import b64encode
from threading import Thread

import rospy
from rtcm_msgs.msg import Message
from ddos_rtk.msg import Status
from std_msgs.msg import Int32

def convert_to_hex(data):
    hex_str = binascii.hexlify(data)
    hex_str = hex_str.decode('utf-8').upper()
    return hex_str

def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead as e:
            return e.partial
    return inner

httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)


class ntripclient:
    def __init__(self):
        rospy.init_node('ntrip_client', anonymous=True)
        self.rtcm_topic = "/rtcm"
        self.pub = rospy.Publisher(self.rtcm_topic, Message, queue_size=10)
        rospy.on_shutdown(self.shutdown_handler)
        self.sub_system_status = rospy.Subscriber("/ddos_defender/rtcm_restart", Int32, self.callback_staus) 
        self.sub_system_status = rospy.Subscriber("/ddos_defender/rtcm_loss_count", Int32, self.callback_loss) 
        
        self.buf_flag = False
        self.sys_stop = False
        self.rtcm_count = 0
        self.connection_timeout = 10

        self.ntrip_user = "a98sa3600@gmail.com"
        self.ntrip_pass = "juang92889"
        self.ntrip_server = "rtk2go.com:2101"
        self.ntrip_stream = "NCKU-meclab"
        self.nmea_gga = "$GPGGA,093913.617,2259.800,N,12013.354,E,1,12,1.0,0.0,M,0.0,M,,*68"
        self.headers = {
            'Ntrip-Version': 'Ntrip/2.0',
            'User-Agent': 'NTRIP ntrip_ros',
            # 'Connection': 'close',
            'Connection': 'keep-alive',  # Modified here
            'Authorization': 'Basic ' + b64encode(self.ntrip_user + ':' + str(self.ntrip_pass))
        }

    def connect(self):
        print("Start To Connect")
        connection = httplib.HTTPConnection(self.ntrip_server,timeout=self.connection_timeout)
        connection.request('GET', '/'+self.ntrip_stream, self.nmea_gga, self.headers)
        response = connection.getresponse()
        if response.status != 200: raise Exception("blah")   
        return  connection,response
    

    def run(self):
        connection,response = self.connect()
        rtcm_msg = Message()
        restart_count = 0
        premble_loss_count = 0
        while not rospy.is_shutdown() :
            rtcm_buffer = ""
            try:
                data = response.read(1)
                if len(data) != 0 and not self.sys_stop:
                    if ord(data[0]) == 211:
                        print("-----------------------------------")  
                        rtcm_buffer += data

                        data = response.read(2)
                        rtcm_buffer += data
                        length = (ord(data[0]) << 8) + ord(data[1])

                        data = response.read(2)
                        rtcm_buffer += data
                        typ = ( ((ord(data[0]) << 8) + ord(data[1])) >> 4  )
                        print (str(datetime.now()), length, typ)
                        length = length + 1
                        if length < 1024:
                            for x in range(length):
                                data = response.read(1)
                                rtcm_buffer += data
                            rtcm_msg.message = rtcm_buffer
                            rtcm_msg.header.seq += 1
                            rtcm_msg.header.stamp = rospy.get_rostime() 
                            print(rtcm_msg.header.seq)
                            # print(convert_to_hex(buf))
                            self.pub.publish(rtcm_msg)
                        else:
                            print ("-----------------------------")
                            print("Length Error")                                
                            continue

                    else: 
                        print(convert_to_hex(data[0]))
                        print ("Wrong RTCM Data,The first byte in any RTCM message should be equal to 211(0xD3).\n")
                        premble_loss_count = premble_loss_count + 1


                else:
                    ''' If zero length data, close connection and reopen it '''
                    restart_count = restart_count + 1
                    print ("Zero length data...or Stop flag is on, Reconnect")
                    print("Restart Count : ", restart_count)
                    connection.close()
                    connection,response = self.connect()
                    if response.status == 200:
                        self.sys_stop = False 
                    else:
                        raise Exception("blah")

            except Exception as e:
                restart_count = restart_count + 1
                print("Unexpected error: {}".format(e))
                print("Restart Count : ", restart_count)
                connection.close()
                connection,response = self.connect()
        print("connection.close...")
        connection.close()

    def shutdown_handler(self):
        print("Shutting down NTRIP client...")
        self.sys_stop = True
        rospy.signal_shutdown("Shutdown requested")

    # Automatically restart by detecting the protection system restart command.
    def callback_staus(self,recover_rtk):
        if recover_rtk.data == 1:
            print("recover_rtk data {}".format(recover_rtk.data))
            self.sys_stop = True
        else:
            self.sys_stop = False

    # Automatically restart by detecting RTCM loss.
    def callback_loss(self,rtcm_loss):
        self.rtcm_count = rtcm_loss.data
        if rtcm_loss.data > 10 and self.sys_stop == False:
            print("rtcm_loss data {}".format(rtcm_loss.data))
            self.sys_stop = True
        else:
            self.sys_stop = False        


if __name__ == '__main__':

    c = ntripclient()
    c_thread = threading.Thread(target=c.run)
    c_thread.daemon = True
    c_thread.start()
    rospy.spin()
    c_thread.join()

