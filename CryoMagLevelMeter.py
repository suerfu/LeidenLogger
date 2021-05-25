import sys
from SerialDevice import SerialDevice

class CryoMagLevelMeter( SerialDevice ):
    
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
        self.max_attempt = 10
    
    def SetDefaultChannel(self, chan):
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

    def read( self ):
        return SerialDevice.read( self ).replace('\r','')
    
    def GetDefaultChannel(self):
        cmd = 'CHAN?'
        self.write('CHAN?')
        return self.read().replace(cmd,'')


    def GetUnit( self ):
        cmd = 'UNIT?'
        for i in range(1,self.max_attempt+1):
            self.write(cmd)
            reply = self.read()
            if reply.find(cmd)>0:
                return reply.replace(cmd,'')
        return ''
    
    def GetLiquidLevel(self, ch):
        
        chan = str(ch)
        if chan not in ['1','2']:
            self.log('# CryoMag Error: specified channel',ch,'is out of range.')
            return None
            
        cmd = 'MEAS? '+chan
        for i in range(1,self.max_attempt+1):
            self.write(cmd)
            reply = self.read()
            if reply.find(cmd) >= 0:
                lev = reply.replace(cmd,'').split()
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