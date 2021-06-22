# May 25, 2021
# Created by Burkhant Suerfu
# suerfu@berkeley.edu

# This is a class for handling communication to CryoMagnetics LM-510 liquid level meter.
# This class will be derived from SerialDevice class
# Serial parameters are:
    # Baudrate: 9600
    # Data bit: 8
    # Start bit: 1
    # Stop bit: 1
    # Parity: N
    # termination: '\n'

    
import sys
from SerialDevice import SerialDevice


class CryoMagLevelMeter( SerialDevice ):
    
    # Constructor. Note the termination character is only linefeed.
    def __init__(self, port, logs=[sys.stdout] ):
        SerialDevice.__init__(self,
                              port=port, 
                              baudrate = 9600,
                              bytesize = 8,
                              parity = 'N',
                              stopbits = 1,
                              timeout = 0.1,
                              term = '\n',
                              logs = logs )
        
        # After failing for 10 successive reads, report error.
        self.max_attempt = 10
    
    # Set detault channel for actions
    def SetDefaultChannel(self, chan):
        
        # First convert the specified channel to a string and check if it's 1 or 2.
        ch = str(chan)
        
        if ch in ['1','2']:
            
            cmd = 'CHAN '+ch
            
            for i in range(1,self.max_attempt+1):
                
                self.write(cmd)
                
                reply = self.read()
                if reply==cmd:
                    return True
                else:
                    self.log('# CryoMag: received', reply, 'in response to', cmd )
            
            self.log('# CryoMag Error: failed to set default channel after %d attempts' % self.max_attempt)
            
            return False
        
        else:
            self.log('# CryoMag Error: specified channel',ch,'is out of range.')
            return False

    
    # Define its own read method.
    def read( self ):
        return SerialDevice.read( self ).replace('\r','')
    
    
    # Return the current default channel
    def GetDefaultChannel(self):
        cmd = 'CHAN?'
        self.write('CHAN?')
        return self.read().replace(cmd,'')


    # Return the current unit
    def GetUnit( self ):
        
        cmd = 'UNIT?'
        
        for i in range(1,self.max_attempt+1):
            
            self.write(cmd)
            
            reply = self.read()
            if reply.find(cmd)>0:
                return reply.replace(cmd,'')
            
        return ''
    
    
    # Key method of this class. Read the current liquid level.
    # The number read will be in cm.
    # If it's in inch on the device's side, it is internally converted.
    def GetLiquidLevel(self, ch):
        
        # Check if channel number is valid or not.
        chan = str(ch)
        if chan not in ['1','2']:
            self.log('# CryoMag Error: specified channel',ch,'is out of range.')
            return None
        
        # Send the command to measure liquid level.
        cmd = 'MEAS? '+chan
        
        for i in range(1,self.max_attempt+1):
            
            self.write(cmd)
            reply = self.read()
            
            if reply.find(cmd) >= 0:
                
                # Since the original command is also echoed, first remove it.
                lev = reply.replace( cmd, '').split()
                
                # It seems very occasionally the obtained liquid level is empty after removing the echoed command.
                if len(lev)<2:
                    
                    self.log('# CryoMag Error: GetLiquidLevel not in correct format:', reply)
                    self.log('# Making one more attempt...')
                    self.reset_input()
                
                # Response has at least the required number of fields. Next, check unit.
                else:
                
                    # return the 
                    if lev[1]=='cm':
                        return float(lev[0])
                    elif lev[1]=='in':
                        return float(lev[0]*2.54)
                    elif lev[1]=='%':
                        self.log('# CryoMag Warning: returning liquid level in %' )
                        return float(lev[0])
                    else:
                        self.log('# CryoMag Error: unknown unit in', reply)
                        return 
            
            else:
                self.log('# CryoMag: received', reply, 'in response to', cmd )
                self.reset_input()
                
        self.log('# CryoMag Error: failed to measure liquid level after %d attempts' % self.max_attempt)
        return None