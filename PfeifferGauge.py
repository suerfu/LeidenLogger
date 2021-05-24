import serial
import time

class PfeifferGauge( object ):
    
    def __init__(self, port='COM6'):
        try:
            self.MaxChannel = 6
            self.device = serial.Serial(port=port, 
                                        baudrate = 9600,
                                        bytesize = 8,
                                        parity = 'N',
                                        stopbits = 1,
                                        timeout = 0.1 )
        except serial.SerialException:
            print('# Serial port not found.')
        else:
            print('# Opened serial port.')
            self.reset_input()
            
    def open(self):
        return self.device.is_open
    
    def close(self):
        self.device.close()
        
    def reset_input(self):
        self.device.reset_input_buffer()
    
    def read(self, char='\r\n', size=None):
        response = self.device.read_until( char, size )
        return response.decode('ascii').replace('\r','').replace('\n','').replace('\x15','')

    def write(self, msg):
        if msg[-2:]!='\r\n':
            msg +='\r\n'
        reply = self.device.write( msg.encode('ascii') )
        time.sleep(0.1)
        return reply

    def getAck(self):
        resp = self.read('\r\n',size=256)
        bytearr = resp.encode('ascii')
        if bytearr==b'\x06':
            return True
        else:
            return False
    
    def readPressure(self, channel):
        
        if channel<1 or channel > self.MaxChannel:
            print('# TPG gauge channel %d out of range' % channel)
            return -1
        
        cmd = 'PR%d' % channel
        self.write(cmd)
        
        if self.getAck()==True:
            self.write('\x05')
            resp = self.read('\x15\r\n', size=256)
            if len(resp)>5:
                stat = resp.split(',')[0]
                pres = resp.split(',')[1]
                if stat=='0':
                    return float(pres)
                else:
                    print( '# TPG gauge error (error code %s)' % stat )
                    return -2
            else:
                print( '# TPG gauge communication error' )
                return -3