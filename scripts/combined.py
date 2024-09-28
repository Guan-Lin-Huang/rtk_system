#!/usr/bin/python

import serial
import httplib
import binascii
from datetime import datetime
from base64 import b64encode
from threading import Thread

import rospy
from rtcm_msgs.msg import Message

''' This is to fix the IncompleteRead error
    http://bobrochel.blogspot.com/2010/11/bad-servers-chunked-encoding-and.html'''
import httplib
def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial
    return inner

httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)

def convert_to_hex(data):
    hex_str = binascii.hexlify(data)
    hex_str = hex_str.decode('utf-8').upper()
    return hex_str

class ntripconnect(Thread):
    def __init__(self, ntc):
        super(ntripconnect, self).__init__()
        self.ntc = ntc
        self.stop = False

    def run(self):
        headers = {
            'Ntrip-Version': 'Ntrip/2.0',
            'User-Agent': 'NTRIP ntrip_ros',
            'Connection': 'close',
            'Authorization': 'Basic ' + b64encode(self.ntc.ntrip_user + ':' + str(self.ntc.ntrip_pass))
        }
        connection = httplib.HTTPConnection(self.ntc.ntrip_server,timeout=1)
        connection.request('GET', '/'+self.ntc.ntrip_stream, self.ntc.nmea_gga, headers)
        response = connection.getresponse()
        if response.status != 200: raise Exception("blah")
        buf = ""
        rmsg = Message()
        restart_count = 0
        while not self.stop:
            try:
                data = response.read(1)
                if len(data) != 0 :
                    if ord(data[0]) == 211:
                        buf += data

                        data = response.read(2)
                        buf += data
                        cnt = ord(data[0]) * 256 + ord(data[1])
                        # print(ord(data[0]), ord(data[1]))

                        data = response.read(2)
                        buf += data
                        typ = (ord(data[0]) * 256 + ord(data[1])) / 16
                        # print(ord(data[0]), ord(data[1]))

                        print (str(datetime.now()), cnt, typ)
                        cnt = cnt + 1
                        for x in range(cnt):
                            data = response.read(1)
                            buf += data
                            if self.stop:
                                break
                        rmsg.message = buf
                        rmsg.header.seq += 1
                        rmsg.header.stamp = rospy.get_rostime() 
                        print(rmsg.header.seq)
                        # print(convert_to_hex(buf))
                        self.ntc.pub.publish(rmsg)
                        buf = ""
                        print ("-----------------------------")
                    else: 
                        ''' Based on https://github.com/goGPS-Project/goGPS_Java/issues/24 '''
                        print(convert_to_hex(data[0]))
                        print ("Wrong RTCM Data,The first byte in any RTCM message should be equal to 211(0xD3).\n")
                    
                else:
                    ''' If zero length data, close connection and reopen it '''
                    restart_count = restart_count + 1
                    print ("Zero length data, Reconnect...")
                    print("Restart Count : ", restart_count)
                    connection.close()
                    connection = httplib.HTTPConnection(self.ntc.ntrip_server)
                    connection.request('GET', '/'+self.ntc.ntrip_stream, self.ntc.nmea_gga, headers)
                    response = connection.getresponse()
                    if response.status != 200: raise Exception("blah")
                    buf = ""

            except Exception as e:
                print("Unexpected error: {}".format(e))
                print("Response timeout occurred. Retrying and handling the timeout...")
                restart_count = restart_count + 1
                print("Restart Count : ", restart_count)
                connection.close()
                connection = httplib.HTTPConnection(self.ntc.ntrip_server)
                connection.request('GET', '/'+self.ntc.ntrip_stream, self.ntc.nmea_gga, headers)
                response = connection.getresponse()
                if response.status != 200: raise Exception("blah")
                buf = ""
        
        print("connection.close...")
        connection.close()



class ntripclient:
    def __init__(self):
        rospy.init_node('ntripclient', anonymous=True)

        self.rtcm_topic = rospy.get_param('~rtcm_topic', 'rtcm')

        self.ntrip_server = rospy.get_param('~ntrip_server')
        self.ntrip_user = rospy.get_param('~ntrip_user')
        self.ntrip_pass = rospy.get_param('~ntrip_pass')
        self.ntrip_stream = rospy.get_param('~ntrip_stream')
        self.nmea_gga = rospy.get_param('~nmea_gga')

        self.pub = rospy.Publisher(self.rtcm_topic, Message, queue_size=10)

        
        self.sub_rtcm = rospy.Subscriber(self.rtcm_topic, Message, self.callbackrtcm) 
        self.serial_port = rospy.get_param('~port','/dev/ttyACM0')
        self.serial_baud = rospy.get_param('~baud',9600) 
        
        '''
        If using u-blox, only publishing the Topic is required, 
        so writing to the port is unnecessary. 
        Therefore, comment out this line. 
        If using NovAtel, writing to the port is necessary, 
        so this line should be uncommented.
        '''
        # self.GPS = serial.Serial(port=self.serial_port, baudrate=self.serial_baud, timeout=2, rtscts=True, dsrdtr=True)
        
        self.connection = None
        self.connection = ntripconnect(self)
        self.connection.start()

    def run(self):
        rospy.spin()
        if self.connection is not None:
            self.connection.stop = True

    def callbackrtcm(self,data):
        correction = data.message

        '''
        If using u-blox, only publishing the Topic is required, 
        so writing to the port is unnecessary. 
        Therefore, comment out this line. 
        If using NovAtel, writing to the port is necessary, 
        so this line should be uncommented.
        '''
        # self.GPS.write(correction)

if __name__ == '__main__':
    c = ntripclient()
    c.run()

