# May 24, 2021
# Created by Burkhant Suerfu
# suerfu@berkeley.edu

# This is a class for handling communication to Pfeiffer 366 Gauge controller
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
        
        # The MaxiGauge has 6 channels
        self.MaxChannel = 6
        self.MaxAttempt = 10
        
        # Following three special characters are enqury, acknowledgement and non-acknowledgemt.
        # In the Pfeiffer device, these are used for hand-shaking.
        self.char_enq = '\x05'
        self.char_ack = '\x06'
        self.char_nak = '\x15'
        
        # When one channel is not enabled on the gauge controller, a warning msg will be printed and this variable set to True
        # This variable is used to prevent the same warning message being printed all the time.
        self.warning = False
        
        self.log("# Created Pfeiffer TPG366 gauge controller.", "Max. number of channel:", self.MaxChannel )

        
    # TPG366 uses a slightly different flowcontrol.
    # Everytime a command is sent, the device will send back either acknowledgement or negative acknowledgement
    def getAck(self):
        repl = self.read( '\r\n', size=256 )
        repl = repl.replace('\r','').replace('\n','')
        if repl==self.char_ack:
            return True
        else:
            self.log('# Failed to get ACK: received ', repl.encode('ascii'))
            return repl
    
    
    # Enquiry
    def query(self):
        self.write('\x05')
        
    
    # Send command until acknowledged
    def write_until_ack( self, cmd, max_try=self.MaxAttempt ):
        
        self.write(cmd)
        
        for i in range( 1, max_try+1 ):
            
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
            
            # Send enqury
            self.query()
            
            # For some reason, the gauge controller appends NAK+\r\n after the main message.
            resp = self.read('\x15\r\n', size=256).replace(self.char_nak,'').replace('\r','').replace('\n','')
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
        
        for h in range( 1, self.MaxAttempt+1):
            
            self.write_until_ack('PRx')
            self.query()
            
            # It seems NAK will always follow the response. So read until one receives NAK
            repl = self.read('\r\n', size=256)
            
            # If on the first read, message is broken and NAK is not received, then repeat to get the whole message.
            if repl.find( self.char_nak ) < 0:
                
                for i in range( 1, self.MaxAttempt+1):
                    
                    #self.log( '# readPressure response not containing NAK symbol. Appending another readline' )
                    repl += self.read('\r\n', size=256)
                    if repl.find( self.char_nak ) >= 0:
                        break
            
            # Remove the meta-characters from the message string.
            # If message is longer than 0, then it's a valid message, so return.
            # If not, then repeat the above process.
            result = repl.replace(self.char_nak,'').replace('\r','').replace('\n','')
            if repl.find( self.char_nak ) >= 0:
                break
        
        pres = [ float(v) for i,v in enumerate(result.split(',')) if i%2==1 ]
        stat = [ v for i,v in enumerate(result.split(',')) if i%2==0 ]
        
        if stat.count('0')!=6 and self.warning==False:
            self.log( '# readPressure at least one channel is not functioning properly. Status: ', stat )
            self.warning = True
        
        return pres
        