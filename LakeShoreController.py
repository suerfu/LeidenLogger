import serial
import time
import sys

class LakeShoreController(object):
    # Baudrate: 57600
    # Data bit: 7
    # Start bit: 1
    # Stop bit: 1
    # Parity: odd
    
    def __init__(self, port):
        try:
            self.connection = serial.Serial(port = port,
                                            baudrate = 57600,
                                            bytesize = 7,
                                            parity = 'O',
                                            stopbits = 1,
                                            timeout = 0.1 )
            self.resistance = -1
            self.log = [sys.stdout]
        except serial.SerialException:
            print( '# Serial port not found.', file=sys.stderr)
            #serial.tools.list_ports.comports()
        else:
            for f in self.log:
                print('# Opened serial port '+port, file=f)
            
    def open(self):
        return self.connection.is_open
    
    def close(self):
        self.connection.close()
        
    def reset_input(self):
        self.connection.reset_input_buffer()
    
    def SetLogFile( self, l):
        self.log = [l]
        
    def AddLogFile( self, l):
        self.log.append(l)
    
    def read(self, char='\r\n', size=None):
        response = self.connection.read_until( char, size )
        return response.decode('ascii').replace('\r','').replace('\n','')

    def write(self, msg):
        if msg[-2:]!='\r\n':
            msg +='\r\n'
        reply = self.connection.write( str.encode(msg) )
        time.sleep(0.1)
        return reply

    def GetFormattedChannel(self, i):
        # check if channel number is valid:
        if int(i)<1 or int(i)>16:
            return '-1'
            
        # format channel to 2 digits
        ch = str(i)
        if len(ch)==1:
            ch = '0'+ch
        return ch
    
    def GetCurrentChannel( self ):
        self.write('SCAN?')
        reply = self.read()
        return reply
    
    def ReadKelvin(self, ch):
        # first format channel to be 2 digits
        ch = self.GetFormattedChannel( ch );
        if ch=='-1':
            return -1
        
        # next send the query command and wait until scanner in the right channel
        # first check current channel
        # if current channel is the desired channel, read directly
        self.write('SCAN?')
        reply = self.read()
        
        # otherwise first switch to the desired channel
        while reply!=ch+',0':
            # send the query
            # remember on first query, it does physical switch while response is null, so read again
            self.write( 'SCAN '+ch+',0' )
            self.write( 'SCAN?' )
            reply = self.read()
            
            if len(reply)<2:
                self.write( 'SCAN?' )
                reply = self.read()
            
        self.write('RDGK?'+ch+'\r\n')
        reply = self.read()
        #print( '#',"channel",ch,"reads",reply)
        return float( reply )
    
    def GetHeaterResistance( self ):
        self.write('HTRSET?0')
        fdbk = self.read().split(',')    
        return float(fdbk[0])
        
    def SetHeaterResistance( self, R, *, file=sys.stdout ):
        R = '{:0>7s}'.format( '{:.3f}'.format( float(R) ) )
        command = 'HTRSET 0,'+R+',0,0,2'
        
        for f in self.log:
            print('# Setting heater resistance to be %s ohm' % R, file=f )
        self.write( command )
        
        return self.GetHeaterResistance()


    def ConfigHeaterRange( self, power ):
        # if resistance is not properly set, signal
        if self.resistance == -1:
            self.resistance = self.GetHeaterResistance()
        
        # compute current required for the specified power
        # power is in Watt
        current = ( power/self.resistance ) ** 0.5
        for f in self.log:
            print('# Expected current is %.3e A' % current, file=f )
        
        rang = '0'
        if current<1.e-15:
            rang='0'
        elif current<31.6e-6:
            rang='1'
        elif current<100e-6:
            rang='2'
        elif current<316e-6:
            rang='3'
        elif current<1e-3:
            rang='4'
        elif current<3.16e-3:
            rang='5'
        elif current<10e-3:
            rang='6'
        elif current<31.6e-3:
            rang='7'
        elif current<100e-3:
            rang='8'
        
        for f in self.log:
            print('# Setting heater range to ' + rang, file=f)
        self.write( 'RANGE 0,'+rang )
        return self.GetHeaterRange()

    
    def GetHeaterRange( self ):
        self.write( 'RANGE?0' )
        return self.read()
    
    def SetHeaterPower( self, power):
        ran = self.ConfigHeaterRange( power)
        
        for f in self.log:
            print('# Setting heater power to be %.3e W' % power, file=f)
        self.write( 'MOUT 0,'+'{:.2e}'.format(power) )
        return self.GetHeaterPower()
    
    def GetHeaterPower( self ):
        self.write('MOUT?0')
        return self.read()

