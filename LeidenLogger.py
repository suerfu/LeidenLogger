import sys
import datetime
import time
import getopt
import signal

from LakeShoreController import LakeShoreController
from PfeifferGauge       import PfeifferGauge
from CryoMagLevelMeter   import CryoMagLevelMeter

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
        self.cmindex = 2
            # index of Pfeiffer when port, freq, specified as a:b:b. By default, it is second
        
        self.lschannels = [""]
        
        self.delta = 0.02
        self.freq = [60, 10, 60]
        self.timeout = 10*60
        self.autoscan = True
        
        self.ConfigureOpt( argv )
        
        self.lscontroller = None
        self.pfcontroller = None
        self.cmcontroller = None
        
        try:
            self.ConfigureLakeShore()
            self.ConfigurePfeiffer()
            self.ConfigureCryoMag()
            
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
            print('# LakeShore AC Bridge Temperature Controller', file = file )
            print('#', TimeStamp(), file = file )
            for c in self.lschannels:
                print("time, T%s, R%s," % (c,c), end=' ', file=file)
            print('', file=file)
            print("# Time is measured in second, temperature in Kelvin and resistance in Ohm.", file=file)
            
        if self.output[ self.pfindex ]:
            file = self.output[ self.pfindex ]
            print('# Pfeiffer TPG366 Vacuum Gauge', file = file )
            print('#', TimeStamp(), file = file )
            
            endchar = ', '
            print("# time since start", end=endchar, file=file)
            for c in self.PFHeader:
                if c==self.PFHeader[-1]:
                    endchar = '\n'
                print( c, end=endchar, file=file)
            print('', file=file)
            print('# Time measured in second and pressure in mbar.', file=file)
            print('# Note: gauge channel is default. It could have been altered without software update.', file=file)
            print('# Note: mbar is default. Pressure unit could be changed on the gauge controller. Please check!', file=file)
            print('# Note: Channel 6 (custom) is by default capillary, but it could be connected to elsewhere.', file=file)
        
        if self.output[ self.cmindex ]:
            file = self.output[ self.cmindex ]
            print('# CryoMagnetics Cryogen Level Meter LM-510', file = file )
            print('#', TimeStamp(), file = file )
            print("# time since start", end='', file=file)
            for c in ['LHe (cm)', 'LN2 (cm)']:
                print( c, end='', file=file)
            print('', file=file)
    
    
    def Execute( self ):
        
        self.starttime = TimeStamp()
        print('# LeidenLogger: executing... Timestamp:', self.starttime)
        
        try:   
            print('# LeidenLogger: executing event loop...')
            
            while True:
                
                # if autoscan is false, then update only pressure (and liquid level),
                # and check if autoscan should be turned back on.
                self.UpdateAutoScan()
                
                self.UpdateTemperature( self.UpdatePressure, self.UpdateLiquidLevel )
                self.UpdatePressure()                        
                self.UpdateLiquidLevel()
                
                time.sleep( 1 )

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
    def UpdateTemperature( self, *callback ):
        
        self.UpdateAutoScan()
        self.NeedUpdateTemp = False
        
        # If not enough time has elapsed, return without updating
        if TimeStamp() - self.LSPrevReading < self.freq[ self.lsindex ]:
            return

        if self.autoscan==True:
                        
            # If code reaches this line, it means enough time has elapsed since last reading.
            for ch in self.lschannels:
          
                # First set the scanner to the right channel and then wait for reading to stablize
                self.LSPrevChannel = self.lscontroller.SetChannel( ch )
                            
                # Temperature update takes time.
                # In the meantime, Update pressure and liquid level as needed by the callback functions
                for i in range(1,5):
                    for func in callback:
                        func()
                    time.sleep( 1 )
                            
                # After the wait time, if there was no manual activity, then update temperature reading
                if self.UpdateAutoScan()==True:
                    self.TempTimeStamp[ch] = int( self.TimeSinceStart( ) )
                    self.Temperature[ch] = self.lscontroller.ReadKelvin( ch )
                    self.Resistance[ch] = self.lscontroller.ReadOhm( ch )
                    self.NeedUpdateTemp = True
                else:
                    break
        
        # If manual operation is in progress, update only the channel of attention.
        else:
            ch = self.lscontroller.GetCurrentChannel()
            ch = int(ch.split(',')[0])
            ch = '%d' % ch
            if ch in self.lschannels:
                self.TempTimeStamp[ch] = int( self.TimeSinceStart( ) )
                self.Temperature[ch] = self.lscontroller.ReadKelvin( ch )
                self.Resistance[ch] = self.lscontroller.ReadOhm( ch )
                self.NeedUpdateTemp = True
            else:
                self.NeedUpdateTemp = False                
                #print('# channel %s is not enabled. Not updating.' % ch, self.lschannels)
                    
        # If program reaches this line, it means autoscan was true for all readings. Update output data file.
        if self.output[ self.lsindex ] and self.NeedUpdateTemp == True:
            self.WriteTemperature( file = self.output[self.lsindex] )
            #self.WriteDict( self.self.Temperature, file = self.output[self.lsindex] )
            self.LSPrevReading = TimeStamp()

                        
    #
    def UpdateLiquidLevel( self ):
        
        # Check frequency or if it is enabled.
        if self.output[ self.cmindex ]==None:
            #print('# debug: liquid level not updated because output is not enabled.')
            return
        
        if TimeStamp() - self.CMPrevReading < self.freq[ self.cmindex ]:
            #print('# debug: liquid level not updated because not enough time has passed since last reading.')
            return

        # Perform a liquid level reading
        self.CMPrevReading = TimeStamp()
        self.LiquidLevel = [ self.cmcontroller.GetLiquidLevel(n) for n in range(1,3) ]
        if None in self.LiquidLevel:    
            print('# LeidenLogger: liquid level not updated due to invalid reading present in', self.LiquidLevel )
        else:
            #print('# debug: updating liquid level with', self.LiquidLevel )
            print( int(self.TimeSinceStart() ), end='', file = self.output[self.cmindex])
            for i in self.LiquidLevel:
                print( ',', '%f' % i, end=' ', file = self.output[self.cmindex])
            print( '', file = self.output[self.cmindex])
                

    # Function to update the status of autoscan
    # Rule 1: no activity for timeout minutes, turn autoscan on.
    # Rule 2: if present channel is different from last check, update time of last manual activity and set false.
    def UpdateAutoScan( self ):
        
        if self.LakeShoreActive()==False:
            self.autoscan = False
            return self.autoscan
        
        self.LSCurChannel = self.lscontroller.GetCurrentChannel()
        
        # No manual change of scanner channel
        if self.LSPrevChannel == self.LSCurChannel:
            # If it has been inactive for long enough, print message and reactivate auto-scan
            if TimeStamp() - self.LSLastActivity > self.timeout:
                if self.autoscan==False:
                    print('# LeidenLogger: inactive for %d, enabling autoscan...' % self.timeout )
                self.autoscan = True
        
        # If there was activity, then update the channel and time of activity
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

    def WriteTemperature( self, file):
        endchar = ', '
        for key in self.lschannels:
            if key==self.lschannels[-1]:
                endchar = '\n'
            print( '%d, %e, %e' % (self.TempTimeStamp[key],self.Temperature[key],self.Resistance[key]), end=endchar, file=file )

    
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
                
                self.TempTimeStamp = {}
                self.Temperature = {}
                self.Resistance  = {}
                self.NeedUpdateTemp = True

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
                self.PFHeader = ['condensor', 'still', 'dump', 'pot', 'IVC', 'custom']
            except:
                print("# LeidenLogger: failed to configure Pfeiffer. Pfeiffer will not be enabled." )
                raise
        else:
            print("# LeidenLogger: port not specified. Pfeiffer will not be enabled." )

    def ConfigureCryoMag( self ):
        if self.port[self.cmindex]!='':
            try:
                print( "# LeidenLogger: configuring CryoMagnetics LM-510 at %s" % self.port[self.cmindex] )
                self.cmcontroller = CryoMagLevelMeter( self.port[self.cmindex] )
                self.CMPrevReading = TimeStamp()-2*self.freq[self.cmindex]
            except:
                print("# LeidenLogger: failed to configure CryoMagnetics LM-510. CryoMagnetics LM-510 will not be enabled." )
                raise
        else:
            print("# LeidenLogger: port not specified. CryoMagnetics LM-510 will not be enabled." )
            
    def Close( self ):
        if self.lscontroller:
            print('# LeidenLogger: closing LakeShore...')
            self.lscontroller.close()
            self.lscontroller = None
            
        if self.pfcontroller:
            print('# LeidenLogger: closing Pfeiffer...')
            self.pfcontroller.close()
            self.pfcontroller = None
            
        if self.cmcontroller:
            print('# LeidenLogger: closing CryoMagnetics...')
            self.cmcontroller.close()
            self.cmcontroller = None
            
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
                print("\t            \t Three files with suffixes _pres.txt, _temp.txt and _liqlevel.txt will be created.")
                print("\t--port LS:PF:CM\t\t serial port address for LakeShore:Pfeiffer:CryoMagLevelMeter connection.")
                print("\t--freq t1:t2:t3\t max interval in seconds between successive readings for LS:PF:CM.\n")

                print("\t--channel L1:L2:L3\t (LakeShore) enable channel L1, L2, L3, ... for data taking. Note the colon as delimiter.")
                print("\t--timeout T\t\t (LakeShore) after T min of inactivity, autoscan will be turned on.\n")

                print("\t--delta  foo\t (Pfeiffer) record data when reading differs by more than foo (fraction) from previous reading.")

                print("\t-h/--help \t display help message.\n")
                sys.exit()

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