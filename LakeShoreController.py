# May 24, 2021
# Created by Burkhant Suerfu
# suerfu@berkeley.edu

# This is a class for handling communication to LakeShore 372 temperature controller.
# This class will be derived from SerialDevice class
# Serial parameters are:
    # Baudrate: 57600
    # Data bit: 7
    # Start bit: 1
    # Stop bit: 1
    # Parity: odd
    # termination: '\r\n'

    
from SerialDevice import SerialDevice
import sys
import time


class LakeShoreController( SerialDevice ):

    # Constructor
    def __init__(self, port, logs=[sys.stdout]):
        SerialDevice.__init__(self, port=port, baudrate=57600, bytesize=7, parity='O', stopbits=1, timeout=0.05, term='\r\n', logs=logs)
        
        # As its own parameter, LakeShore has sample heater resistance object. Initialize to -1.
        self.resistance = -1
        
        # This maximum number of channel can be changed for other LakeShore models.
        self.MaxChannel = 16
        
        # 
        self.max_attempt = 10
        
        self.log("# Created LakeShore372 controller.", "Max. number of channels:", self.MaxChannel)
    
    # In communication, LakeShore expects two-digit channel form. This function formats the input channel
    def GetFormattedChannel(self, i):
        # check if channel number is valid:
        if int(i)<1 or int(i)>self.MaxChannel:
            self.log('# Error: channel', i, 'is out of range.')
            return '-1'
            
        # format channel to 2 digits
        return '{:0>2d}'.format( int(i) )

    
    # Query for the present scanner channel
    def GetCurrentChannel( self ):
        self.write('SCAN?')
        reply = self.read()
        return reply
    
    # Set the scanner to the specified channel
    def SetChannel( self, chan):
        # first format channel to be 2 digits
        ch = self.GetFormattedChannel( chan );
        if ch=='-1':
            return -1
        
        # next send the query command and wait until scanner in the right channel
        # first check current channel
        # if current channel is the desired channel, read directly
        reply = self.GetCurrentChannel()
        
        # otherwise first switch to the desired channel
        max_try = 100
        for i in range(1,max_try+1):
            if reply==ch+',0':
                return reply
                
            # send the query
            # sometimes on first query, it does physical switch while response is null, so read twice
            self.write( 'SCAN '+ch+',0' )
            reply = self.GetCurrentChannel()
            
            if len(reply)<4:
                reply = self.GetCurrentChannel()

        self.log('# Failed to set the right channel to %s after %d attempts' % (ch,max_try) )
        return reply
        
        
    # Read the temperature in Kelvin of the specified channel
    # Note: this function does NOT guarantee accurate reading: one must make sure the scanner is set at the right channel.
    def ReadKelvin(self, ch):
        self.write( 'RDGK?'+ch )
        reply = self.read()
        return float( reply )

    # Read the resistance in ohm.
    # Resistance is useful when the temperature is out of measurement range.
    def ReadOhm(self, ch):
        self.write( 'RDGR?'+ch )
        reply = self.read()
        return float( reply )
    
    # Query for the present setting of the sample heater resistance
    # This value is needed by the LakeShore controller to set the right current for the specified power
    def GetHeaterResistance( self ):
        for t in range(1,self.max_attempt+1):
            self.write('HTRSET?0')
            fdbk = self.read().split(',')
            if len(fdbk) > 2:
                return float( fdbk[0] )
            else:
                self.log('# Failed to get heater resistance on attempt %d. Trying again...' % t)

        self.log('# Failed to get heater resistance after %d attempts.' % self.max_attemp)
        return None

    # Configure the sample heater resistance
    def SetHeaterResistance( self, R ):
        
        # Format the resistance to have the right width and zero-padding
        R = '{:0>7s}'.format( '{:.3f}'.format( float(R) ) )
        
        command = 'HTRSET 0,'+R+',0,0,2'
        self.write( command )
        
        self.log('# Setting heater resistance to be %s Ohm' % R )
        return self.GetHeaterResistance()


    # There is a maximum current range. The current required for the specified power must be smaller than this.
    # For the meaning of the code, see the manual.
    def ConfigHeaterRange( self, power ):
        
        # if resistance is not properly set, signal
        if self.resistance == -1:
            self.resistance = self.GetHeaterResistance()
        
        # compute current required for the specified power
        # power is in Watt
        current = ( power/self.resistance ) ** 0.5
        
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
            
        self.write( 'RANGE 0,'+rang )
        
        self.log('# Expected current for %.3e W is %.3e A' % ( power, current) )
        self.log('# Setting heater range to ' + rang )

        return self.GetHeaterRange()

    # Query for the range code of the sample heater
    def GetHeaterRange( self ):
        self.write( 'RANGE?0' )
        return self.read()
    
    # Set the sample heater output power
    def SetHeaterPower( self, power):
        ran = self.ConfigHeaterRange( power)
        self.write( 'MOUT 0,'+'{:.2e}'.format(power) )
        self.log('# Setting heater power to be %.3e W' % power )
        return self.GetHeaterPower()
    
    # Query for the current setting of sample heater output power in Watt.
    def GetHeaterPower( self ):
        self.write('MOUT?0')
        return self.read()

