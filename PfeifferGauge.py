# May 24, 2021
# Created by Burkhant Suerfu
# suerfu@berkeley.edu

# This is a class for handling communication to LakeShore 372 temperature controller.
# This class will be derived from SerialDevice class
# Serial parameters are:
    # Baudrate: 9600
    # Data bit: 8
    # Start bit: 1
    # Stop bit: 1
    # Parity: N
    # termination: '\r\n'

from SerialDevice import SerialDevice
import sys


class PfeifferGauge( SerialDevice ):
    
    # Constructor. Create the gauge controller with default parameters
    def __init__(self, port, logs=[sys.stdout]):
        SerialDevice.__init__(self, port=port, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=0.05, term='\r\n', logs=logs)
        
        self.MaxChannel = 6
        self.MaxAttempt = 10
        self.char_enq = '\x05'
        self.char_ack = '\x06'
        self.char_nak = '\x15'
        
        self.log("# Created Pfeiffer TPG366 gauge controller.", "Max. number of channel:", self.MaxChannel )

    # TPG366 uses a slightly different flowcontrol.
    # Everytime a command is sent, the device will send back either acknowledgement or negative acknowledgement
    def getAck(self):
        repl = self.read( '\r\n', size=256 )
        repl.replace('\r','').replace('\n','')
        if repl==self.char_ack:
            return True
        else:
            self.log('# Failed to get ACK: received ', repl.encode('ascii'))
            return repl
    
    
    # Enquiry
    def query(self):
        self.write('\x05')
        
    
    # Send command until acknowledged
    def write_until_ack( self, cmd, max_try=10 ):
        
        self.write(cmd)
        
        for i in range(1, max_try):
            if self.getAck()==True:
                return True
            
            self.log("# Attempt %d to send command %s" %(i, cmd) )
            self.reset_input()
            self.write(cmd)
    
    # Read pressure out of the gauge.
    def ReadPressure(self, channel):
        
        # First check if channel is out of range
        if channel<1 or channel > self.MaxChannel:
            self.log('# TPG gauge channel %d out of range' % channel)
            return -1
        
        cmd = 'PR%d' % channel
        if self.write_until_ack(cmd)==True:
            self.query()
            resp = self.read('\x15\r\n', size=256).replace(self.char_nak,'')
            if len(resp)>5:
                stat = resp.split(',')[0]
                pres = resp.split(',')[1]
                if stat=='0':
                    return float(pres)
                else:
                    self.log( '# TPG gauge error (error code %s)' % stat )
                    return None
            else:
                self.log( '# TPG gauge communication error' )
                return None
        else:
            self.log( '# readPressure: Failed to get ACK from TPG gauge' )
            return None

            
    # Read pressure from all channels from the gauge.
    # Note that TPG366 sometimes truncates the message
    # In such cases, read again and add them together to form the response.
    def ReadPressure( self ):
        
        self.write_until_ack('PRx')
        self.query()
        
        repl = self.read('\r\n', size=256)
        if len(repl) > 1:
            while repl.find( self.char_nak ) < 0:
                #self.log( '# readPressure response not containing NAK symbol. Appending another readline' )
                repl += self.read('\r\n', size=256)
            result = repl.replace(self.char_nak,'')
        
        pres = [ float(v) for i,v in enumerate(result.split(',')) if i%2==1 ]
        stat = [ v for i,v in enumerate(result.split(',')) if i%2==0 ]
        if stat.count('0')!=6:
            self.log( '# readPressure at least one channel is not functioning properly. Status: ', stat )
        
        return pres
        

