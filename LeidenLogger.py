import sys
import datetime
import time
import getopt
import signal

from LakeShoreController import LakeShoreController
from PfeifferGauge import PfeifferGauge

def Now():
    return datetime.datetime.now()

def TimeStamp():
    return Now().timestamp()


class LeidenLogger( object ):
    
    # Constructor. Initialize internal parameters based on commandline input
    def __init__(self, argv):
        
        print('# LeidenLogger: initializing...')
        
        self.ndevice = 3
        self.prefix = ""
        
        self.port = ["","",""]
        self.output = ["","",""]
        self.suffix = ["_temp.txt","_pres.txt","_liqlev.txt"]
        self.lsindex = 0
            # index of LakeShore when port, freq specified as a:b:b. By default, it is first
        self.pfindex = 1
            # index of Pfeiffer when port, freq, specified as a:b:b. By default, it is second
        
        self.lschannels = [""]
        
        self.delta = 0.02
        self.freq = [60, 10]
        self.timeout = 10*60
        self.autoscan = True
        
        self.ConfigureOpt( argv )
        
        self.lscontroller = None
        self.pfcontroller = None
        try:
            self.ConfigureLakeShore()
            self.ConfigurePfeiffer()
            self.ConfigureOutput()
            self.WriteHeader()
            self.SetupSignalHandler()
        except:
            self.Close()
            raise
    
    
    def ConfigureOutput( self ):
        if self.prefix=="":
            self.output = [ sys.stdout for f in self.port ]
        else:
            self.output = [ open( self.prefix+f, "w", buffering=1) for f in self.suffix ]
        
        print('# LeidenLogger: opened following files' )
        print('#', [ f.name for f in self.output ] )
    
    
    def WriteHeader( self ):
        if self.output[ self.lsindex ]:
            file = self.output[ self.lsindex ]
            print('#', TimeStamp(), file = file )
            print("# time since start", end='', file=file)
            for c in self.lschannels:
                print(", channel "+c, end='', file=file)
            print('', file=file)
            
        if self.output[ self.pfindex ]:
            file = self.output[ self.pfindex ]
            print('#', TimeStamp(), file = file )
            print("# time since start", end='', file=file)
            for c in range(1,7):
                print(", channel %d" % c, end='', file=file)
            print('', file=file)
    
    
    def Execute( self ):
        
        self.starttime = TimeStamp()
        print('# LeidenLogger: executing... Timestamp:', self.starttime)
        
        try:
            
            print('# LeidenLogger: executing event loop...')
            
            while True:
                # if autoscan is false, then update only pressure (and liquid level),
                # and check if autoscan should be turned back on.
                if self.UpdateAutoScan()==False:
                    self.UpdatePressure()
                    time.sleep( 1 )
                    
                # AutoScan is active. Iterate over LakeShore enabled channels to update reading.
                else:
                    for ch in self.lschannels:
                        
                        # Check manual activity before each action
                        if self.UpdateAutoScan()==True:
                            
                            # First set the scanner to the right channel and then wait for reading to stablize
                            self.LSPrevChannel = self.lscontroller.SetChannel( ch )
                            
                            # In the meantime, update pressure as needed
                            for i in range(1,5):
                                self.UpdatePressure()
                                time.sleep( 1 )
                            
                            # After the wait time, if there was no manual activity, then update temperature reading
                            if self.UpdateAutoScan()==True:
                                self.Temperature['ts_'+ch] = self.TimeSinceStart( )
                                self.Temperature[ch] = self.lscontroller.ReadKelvin( ch )
                    
                    # Before update, check one more time
                    # If autoscan is false at this point, it means temperature has not been all updated properly.
                    if self.UpdateAutoScan()==True:
                        self.UpdateTemperature()
                        
        except:
            print('# LeidenLogger: exception has ocurred. Terminating...')
            self.Close()
            raise
    
    #
    def UpdatePressure( self ):
        if self.PfeifferActive()==False:
            return
        
        update = False
        curr   = TimeStamp()
        
        self.Pressure1 = self.pfcontroller.ReadPressure()
            # pressure is given as an list with 6 elements
        #print( '# Pressure read at', TimeStamp(),self.Pressure1)
        
        if curr-self.PFPrevReading > self.freq[ self.pfindex ]:
            update = True
            #print( '# Pressure updating due to reaching required interval.')
        elif self.MaxFracChange() > self.delta:
            update = True
            #print( '# Pressure updating due to large change.')
        
        if update==True:
            if self.output[ self.pfindex ]:
                print( int(self.TimeSinceStart() ), end='', file = self.output[self.pfindex])
                for i in self.Pressure1:
                    print( ',', '%e' % i, end=' ', file = self.output[self.pfindex])
                print( '', file = self.output[self.pfindex])
            self.PFPrevReading = curr
        
        # Update pressure reading in all cases (to constantly monitor amount of change)
        self.Pressure0 = [ i for i in self.Pressure1 ]
            
    #
    def MaxFracChange( self ):
        res = [ abs((j-i)/i) for i,j in zip(self.Pressure0, self.Pressure1) ]
        return max(res)
    
    #
    def UpdateTemperature( self ):
        if self.output[ self.lsindex ]:
            self.WriteDict( self.Temperature, file = self.output[self.lsindex] )
    
    # Function to update the status of autoscan
    # Rule 1: no activity for timeout minutes, turn autoscan on.
    # Rule 2: if present channel is different from last check, update time of last manual activity and set false.
    def UpdateAutoScan( self ):
        
        if self.LakeShoreActive()==False:
            return False
        
        self.LSCurChannel = self.lscontroller.GetCurrentChannel()
        
        if self.LSPrevChannel == self.LSCurChannel:
            if TimeStamp() - self.LSLastActivity > self.timeout:
                self.autoscan = True
                print('# LeidenLogger: inactive for %d, enabling autoscan...' % self.timeout )
        else:
            if self.autoscan == True:
                print('# LeidenLogger: manual activity detected. Disabling autoscan...' )
            self.LSLastActivity = TimeStamp()
            self.LSPrevChannel = self.LSCurChannel
            self.autoscan = False
            
        return self.autoscan
    
    
    def WriteDict( self, Dict, file):
        for key in Dict:
            if key == list(Dict.items())[0][0]:
                print( '%d' % Dict[key], end=", ", file=file )
            elif key == list(Dict.items())[-1][0]:
                print( '%f' % Dict[key], file=file )
            else:
                print( '%f' % Dict[key], end=", ", file=file )
                
    
    def ConfigureLakeShore( self ):
        if self.port[self.lsindex]!='':
            try:
                print( "# LeidenLogger: configuring LakeShore at %s" % self.port[self.lsindex] )
                self.lscontroller = LakeShoreController( self.port[self.lsindex] )
                
                self.LSPrevChannel = self.lscontroller.GetCurrentChannel()
                self.LSCurChannel = ""
                print( "# Current LakeShore scanner channel is", self.LSPrevChannel)
                    # Scanner channel when the object is created.
                    
                self.LSLastActivity = TimeStamp()
                    # Set time of last activity.
                    # This variable is used to see if someone is actively using the scanner.
                    
                self.LSPrevReading = self.LSLastActivity-2*self.freq[self.lsindex]
                    # This variable is used to see if one should perform a reading
                
                self.Temperature = {}

            except:
                print("# LeidenLogger: failed to configure LakeShore. LakeShore will not be enabled." )
                raise
        else:
            print("# LeidenLogger: port not specified. LakeShore will not be enabled." )

            
    def ConfigurePfeiffer( self ):
        if self.port[self.pfindex]!='':
            try:
                print( "# LeidenLogger: configuring Pfeiffer at %s" % self.port[self.pfindex] )
                self.pfcontroller = PfeifferGauge( self.port[self.pfindex] )
                self.PFPrevReading = TimeStamp()-2*self.freq[self.pfindex]
            except:
                print("# LeidenLogger: failed to configure Pfeiffer. Pfeiffer will not be enabled." )
                raise
        else:
            print("# LeidenLogger: port not specified. Pfeiffer will not be enabled." )

            
    def Close( self ):
        if self.lscontroller:
            print('# LeidenLogger: closing LakeShore...')
            self.lscontroller.close()
            self.lscontroller = None
            
        if self.pfcontroller:
            print('# LeidenLogger: closing Pfeiffer...')
            self.pfcontroller.close()
            self.pfcontroller = None
        
        for f in self.output:
            if f:
                f.close()
        
    
    def ConfigureOpt( self, argv ):
        print('# LeidenLogger configuring commandline options.')
        print(argv)
    
        # Obtain the commandline options and arguments.
        # Setpoints will be the arguments which are specified in the end
        opts, _ = getopt.getopt( argv[1:], "h", ["channel=","timeout=","delta=","port=","prefix=","freq=","help"] )

        # Iterate through the commandline options to set the parameters.
        for opt, arg in opts:

            # If prefix is used instead, then append formated date and time to the prefix.    
            if opt in ("--prefix"):
                self.prefix = arg+"_"+time.strftime('%Y%m%d')+"_"+time.strftime('%H%M%S')

            # maximum change of temperature in mK per min at equilibrium
            if opt in ("--delta"):
                self.delta = float(arg)

            # The time in seconds between successive readings while waiting for equilibrium.
            if opt in ("--freq"):
                temp = arg.split(':')
                for n,intv in enumerate( temp ):
                    if intv!='':
                        self.freq[n] = float( intv )

            # Port specified as LakeShore:Pfeiffer
            if opt in ("--port"):
                temp = arg.split(':')
                for n,c in enumerate(temp):
                    self.port[n] = c

            # Channels enabled for LakeShore
            # multiple channels separated by : as a whole single string
            if opt in ("--channel"):
                self.lschannels = arg.split(':')

            # Switch on auto-scanning (LakeShore) after being inactive for certain amount of time.
            if opt in ("--timeout"):
                self.timeout = int(arg)*60

            if opt in ("-h","--help"):
                print("usage: "+argv[0]+" [options optional_parameter]\n")
                print("options:\n")
                print("\t--prefix foo\t set the prefix of output filename to be foo_yyyymmdd_hhmmss.")
                print("\t            \t Three files with suffixes _pres, _temp and _liqlevel will be created.")
                print("\t--port LS:PF\t\t serial port address for LakeShore:Pfeiffer connection.")
                print("\t--freq t\t interval in seconds between successive readings.\n")

                print("\t--channel L1:L2:L3\t (LakeShore) enable channel L1, L2, L3 for data taking. Note the colon as delimiter.")
                print("\t--timeout T\t\t (LakeShore) after T min of inactivity, autoscan will be turned on.\n")

                print("\t--delta  foo\t (Pfeiffer) record data when reading differs by more than foo (fraction) from previous reading.")

                print("\t-h/--help \t display help message.\n")

    def LakeShoreActive( self ):
        if self.lscontroller:
            return True
        else:
            return False
    
    def PfeifferActive( self ):
        if self.pfcontroller:
            return True
        else:
            return False
            
    
    def SetupSignalHandler( self ):
        signal.signal( signal.SIGINT, self.Terminate )
        signal.signal( signal.SIGBREAK, self.Terminate )
        
    def Terminate( self, signum, frame ):
        print('# LeidenLogger: interruption signal detected. Preparing to exit...')
        
        # If user signals program end, close connection to devices and write output to files.
        self.Close()
        sys.exit()

    def TimeSinceStart( self ):
        return TimeStamp()-self.starttime



# Python main function start here.
def main():
    if len(sys.argv)<2:
        print('# Did not detect commandline argument. Executing with pre-configured settings.')
        ll = LeidenLogger( ['./leidenlogger','--port','COM7:COM6','--freq','60:10','--timeout', '10','--channel','1:2:3:4:5:7:9:10:11:12:14:15','--prefix','run16_cooldown','--delta','0.01'] )
        ll.Execute()
        ll.Close()
    else:
        print('# Commandline options detected. Executing the following: ')
        print('#', sys.argv )
        ll = LeidenLogger( sys.argv )
        ll.Execute()
        ll.Close()

if __name__== "__main__":
    main()