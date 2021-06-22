# May 24, 2021
# Created by Burkhant Suerfu
# suerfu@berkeley.edu

# This program will log the temperature, pressure and the cryogen liquid level of the Leiden fridge.

import sys
import datetime
import time
import getopt
import signal

# Miscellaneous, needed if server is to be run within this program.
# Currently, all server related direct functions are not working.

from _thread import *
import threading
import socket

# Modules needed for managing device connections.

from LakeShoreController import LakeShoreController
from PfeifferGauge       import PfeifferGauge
from CryoMagLevelMeter   import CryoMagLevelMeter


# Time-keeping. Returns current datetime in python structure.
def Now():
    return datetime.datetime.now()


# Timestamp in float.
def TimeStamp():
    return Now().timestamp()


# The actual logger function
class LeidenLogger( object ):
    
    # Constructor. Initialize internal parameters based on commandline input
    def __init__(self, argv):
        
        print('# LeidenLogger: initializing...')
        
        # Default number of devices to read numbers from
        self.ndevice = 3
        
        # Default prefix of the output filenames.
        # If it is "", output will not be enables.
        self.prefix = ""
        
        # Serial port used to communicate to the device.
        self.port = ["","",""]
        
        # Output files and suffix to filename.
        self.output = ["","",""]
        self.suffix = ["_temp.txt","_pres.txt","_liqlev.txt"]
        
        self.lsindex = 0
            # index of LakeShore when port, freq specified as a:b:b. By default, it is first
        self.pfindex = 1
            # index of Pfeiffer when port, freq, specified as a:b:b. By default, it is second
        self.cmindex = 2
            # index of Pfeiffer when port, freq, specified as a:b:b. By default, it is second
        
        # LakeShore enabled channels
        self.lschannels = [""]
        
        # Used by Pfeiffer to record pressure when there is a large change.
        self.delta = 0.02
        
        # Default readout frequency of the three devices.
        self.freq = [60, 10, 60]
        
        # Time before LakeShore switches back to autoscan mode.
        self.timeout = 10*60
        self.autoscan = True
        
        # Server file. This file will be periodically read by a server script to print fridge status.
        self.ServerOutput = "leiden_status.txt"
        
        
        # === Variables initialized, program action starts from here ===
        
        # Read configuration from commandline.
        self.ConfigureOpt( argv )
        
        # LakeShore, Pfeiffer and CryoMagnetics device handler files.
        self.lscontroller = None
        self.pfcontroller = None
        self.cmcontroller = None
        
        # Try to establish communication to the devices. If failed, terminate.
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
    
    
    # Start the server.
    # This function is no longer used, and it has never worked.
    def StartServer( self ):
        self.server_socket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        self.server_socket.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
        self.server_socket.bind( ('', self.ServerPort) )
        self.server_socket.listen( 1 )
        print('# Starting http server on port %d' % self.ServerPort )
        
        while True:
            print('# Waiting to accept')
            client, addr = self.server_socket.accept()
            req_data = client.recv(1024).decode('utf-8')
            print('# received', req_data)
            #if req_data.find('GET /status') >=0 :
            response = 'HTTP/1.1 200 OK\n\nHello World!'
                #response +=
            client.sendall( response.encode('utf-8') )
            print('# sent')
            
            client.close()
        
    
    # Create the output files.
    def ConfigureOutput( self ):
        
        # If prefix is not specified, then all output redirected to standard output.
        if self.prefix=="":
            self.output = [ sys.stdout for f in self.port ]
        
        # If output is specified, then check if the corresponding port is specified.
        # If port is not specified, then do not create the output file.
        # The existance of output file will be used later to decide whether to read from devices.
        else:
            #self.output = [ open( self.prefix+f, "w", buffering=1) for f in self.suffix ]
            for n,f in enumerate( self.suffix ):
                if self.port[n] != "" and self.port[n] != None:
                    self.output[n] = open( self.prefix+f, "w", buffering=1)
                else:
                    self.output[n] = None
                    
        print('# LeidenLogger: opened following files' )
        print('#', [ f.name for f in self.output if f!=None ] )
    
    
    # Write the header of the three output files.
    # Header should contain the column names and the timestamp program started.
    def WriteHeader( self ):
        
        # LakeShore header
        if self.output[ self.lsindex ]:
            file = self.output[ self.lsindex ]
            print('#', TimeStamp(), file = file )
            print('#', end=', ', file = file)
            for c in self.lschannels:
                print("time, T%s, R%s," % (c,c), end=' ', file=file)
            print('', file=file)
            print('# LakeShore AC Bridge Temperature Controller', file = file )
            print("# Time is measured in second, temperature in Kelvin and resistance in Ohm.", file=file)
            
        # Pfeiffer header
        if self.output[ self.pfindex ]:
            file = self.output[ self.pfindex ]
            print('#', TimeStamp(), file = file )
            endchar = ', '
            print("# time since start", end=endchar, file=file)
            for c in self.PFHeader:
                if c==self.PFHeader[-1]:
                    endchar = '\n'
                print( c, end=endchar, file=file)
            print('', file=file)
            print('# Pfeiffer TPG366 Vacuum Gauge', file = file )
            print('# Time measured in second and pressure in mbar.', file=file)
            print('# Note: gauge channel is default. It could have been altered without software update.', file=file)
            print('# Note: mbar is default. Pressure unit could be changed on the gauge controller. Please check!', file=file)
            print('# Note: Channel 6 (custom) is by default capillary, but it could be connected to elsewhere.', file=file)
        
        # CryoMagnetics header
        if self.output[ self.cmindex ]:
            file = self.output[ self.cmindex ]
            print('#', TimeStamp(), file = file )
            print("# time since start", end='', file=file)
            for c in [', LHe (cm)', ', LN2 (cm)']:
                print( c, end='', file=file)
            print('', file=file)
            print('# CryoMagnetics Cryogen Level Meter LM-510', file = file )
    
    
    # Main part of the program
    def Execute( self ):
        
        # Obtain the timestamp of the start time.
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
                
                self.UpdateServer()

                time.sleep( 1 )

        except:
            print('# LeidenLogger: exception has ocurred. Terminating...')
            self.Close()
            raise
    
    
    # Update the server file.
    def UpdateServer( self ):
        
        if self.ServerOutput==None:
            return
        
        # Write the file output. The content of this file will be printed to the website directly.
        with open( self.ServerOutput, 'w' ) as server:
            print( 'Current time:', Now(), file=server )
            print( '\nTemperature:', file=server )
            
            if self.output[ self.lsindex ] != None:
                for c in self.lschannels:
                    print( '\tChannel %s:\t%.3e K / %.3e Ohm' % (c, self.Temperature[c], self.Resistance[c]), file=server)
                      
            if self.output[ self.pfindex ] != None:
                print('\nPressure:', file=server)
                for n,p in enumerate(self.Pressure0):
                    print( '\t%s:\t%.3e mbar' % (self.PFHeader[n], p), file=server)

            if self.output[ self.cmindex ] != None:
                print('\nCryogen level:', file=server)
                print( '\tLHe: %.2f cm' % self.LiquidLevel[0], file=server)
    
    
    # Read pressure from Pfeiffer
    def UpdatePressure( self ):
        
        if self.PfeifferActive()==False:
            return
        
        update = False
        curr   = TimeStamp()
        
        self.Pressure1 = self.pfcontroller.ReadPressure()
            # pressure is given as an list with 6 elements
        #print( '# Pressure read at', TimeStamp(),self.Pressure1)
        
        # If enough time has elapsed, then always update.
        if curr-self.PFPrevReading > self.freq[ self.pfindex ]:
            update = True
            #print( '# Pressure updating due to reaching required interval.')

        # Alternatively, if the pressure change is big enough, also update pressure
        elif self.MaxFracChange() > self.delta:
            update = True
            #print( '# Pressure updating due to large change.')
        
        # Write the output
        if update==True:
            if self.output[ self.pfindex ]:
                print( int(self.TimeSinceStart() ), end='', file = self.output[self.pfindex])
                for i in self.Pressure1:
                    print( ', %e' % i, end='', file = self.output[self.pfindex])
                print( '', file = self.output[self.pfindex])
            self.PFPrevReading = curr
        
        # Update pressure reading in all cases (to constantly monitor amount of change)
        self.Pressure0 = [ i for i in self.Pressure1 ]


    # Returns the maximum fractional change among all channels
    def MaxFracChange( self ):
        res = [ abs((j-i)/i) for i,j in zip(self.Pressure0, self.Pressure1) ]
        return max(res)
    
    
    # Read and update temperature by LakeShore
    def UpdateTemperature( self, *callback ):
        
        self.UpdateAutoScan()
        self.NeedUpdateTemp = False
        
        # If not enough time has elapsed, return without updating
        if TimeStamp() - self.LSPrevReading < self.freq[ self.lsindex ]:
            return

        # If autoscan is true, then read and update all enabled channels
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
            
            # First find out the current scanner channel
            ch = self.lscontroller.GetCurrentChannel()
            ch = int(ch.split(',')[0])
            ch = '%d' % ch
            
            # If the scanner channel being viewed is enabled, update the temperature
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

                        
    # Read and update liquid level from CryoMagnetics
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
    
    
    # Write the content of a dictionary to file.
    def WriteDict( self, Dict, file):
        for key in Dict:
            if key == list(Dict.items())[0][0]:
                print( '%d' % Dict[key], end=", ", file=file )
            elif key == list(Dict.items())[-1][0]:
                print( '%f' % Dict[key], file=file )
            else:
                print( '%f' % Dict[key], end=", ", file=file )

                
    # Write temperature to file
    def WriteTemperature( self, file):
        endchar = ', '
        for key in self.lschannels:
            if key==self.lschannels[-1]:
                endchar = '\n'
            print( '%d, %e, %e' % (self.TempTimeStamp[key],self.Temperature[key],self.Resistance[key]), end=endchar, file=file )

    
    # Initialize and configure LakeShore controller
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
                    # Three dictionaries that contains information for output.
                    # Since temperature reading is slow, each channel has its own timestamp under TempTimeStamp
                    
                self.NeedUpdateTemp = True
                    # Variable used to check if changes have ocurred that requires updating the output file.

            except:
                print("# LeidenLogger: failed to configure LakeShore. LakeShore will not be enabled." )
                raise
                
        else:
            print("# LeidenLogger: port not specified. LakeShore will not be enabled." )


    # Initialize connection to Pfeiffer gauge controller.
    def ConfigurePfeiffer( self ):
        
        if self.port[self.pfindex]!='':
            
            try:
                print( "# LeidenLogger: configuring Pfeiffer at %s" % self.port[self.pfindex] )
                self.pfcontroller = PfeifferGauge( self.port[self.pfindex] )
                
                self.PFPrevReading = TimeStamp()-2*self.freq[self.pfindex]
                self.PFHeader = ['condsr', 'still', 'dump', 'pot', 'IVC', 'custom']
                    # Initialize the time of previous reading to be past to ensure guaranteed first read.
                    
            except:
                print("# LeidenLogger: failed to configure Pfeiffer. Pfeiffer will not be enabled." )
                raise
                
        else:
            print("# LeidenLogger: port not specified. Pfeiffer will not be enabled." )

            
    # Initialize variables relevant to CryoMagnetics            
    def ConfigureCryoMag( self ):
        
        # First check if CryoMagnetics is enabled or not.
        if self.port[self.cmindex] != '':
            
            try:
                print( "# LeidenLogger: configuring CryoMagnetics LM-510 at %s" % self.port[self.cmindex] )
                self.cmcontroller = CryoMagLevelMeter( self.port[self.cmindex] )
                self.CMPrevReading = TimeStamp()-2*self.freq[self.cmindex]
                    # Initialize the time of previous reading to be past to ensure guaranteed first read.
                
            except:
                print("# LeidenLogger: failed to configure CryoMagnetics LM-510. CryoMagnetics LM-510 will not be enabled." )
                raise
                
        else:
            print("# LeidenLogger: port not specified. CryoMagnetics LM-510 will not be enabled." )
    
    
    # Close connections to the devices and output files.
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
        
    
    # Read the configuration from commandline
    def ConfigureOpt( self, argv ):
        print('# LeidenLogger configuring commandline options.')
        print(argv)
    
        # Obtain the commandline options and arguments.
        # Setpoints will be the arguments which are specified in the end
        opts, _ = getopt.getopt( argv[1:], "h", ["channel=","timeout=","delta=","port=","prefix=","freq=","no-server", "server-port","help"] )

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
                
            if opt in ("--no-server"):
                self.ServerOutput = None
                
            if opt in ("--server-file"):
                self.ServerOutput = argv
                
            if opt in ("-h","--help"):
                print("usage: "+argv[0]+" [options optional_parameter]\n")
                print("options:\n")
                print("\t--prefix foo\t set the prefix of output filename to be foo_yyyymmdd_hhmmss.")
                print("\t            \t Three files with suffixes _pres.txt, _temp.txt and _liqlevel.txt will be created.")
                print("\t--port LS:PF:CM\t\t serial port address for LakeShore:Pfeiffer:CryoMagLevelMeter connection.")
                print("\t--freq t1:t2:t3\t max interval in seconds between successive readings for LS:PF:CM.\n")

                print("\t--channel L1:L2:L3\t (LakeShore) enable channel L1, L2, L3, ... for data taking. Note the colon as delimiter.")
                print("\t--timeout T\t\t (LakeShore) after T min of inactivity, autoscan will be turned on.\n")

                print("\t--delta  foo\t (Pfeiffer) record data when reading differs by more than foo (fraction) from previous reading.\n")

                print("\t-h/--no-server\t start program without running the server.\n")
                
                print("\t-h/--server-file foo\t use foo as status file for server output.\n")
                
                print("\t-h/--help \t display help message.\n")
                sys.exit()

                
    # If LakeShore is enabled and active or not
    def LakeShoreActive( self ):
        if self.lscontroller:
            return True
        else:
            return False
    
    
    # If Pfeiffer is active or not.
    def PfeifferActive( self ):
        if self.pfcontroller:
            return True
        else:
            return False

        
    # If CryoMagnetics is active or not
    def PfeifferActive( self ):
        if self.cmcontroller:
            return True
        else:
            return False
            
    
    # Assign signal handler
    def SetupSignalHandler( self ):
        signal.signal( signal.SIGINT, self.Terminate )
        signal.signal( signal.SIGBREAK, self.Terminate )

        
    # Actual function called in case of interruption
    def Terminate( self, signum, frame ):
        print('# LeidenLogger: interruption signal detected. Preparing to exit...')
        
        # If user signals program end, close connection to devices and write output to files.
        self.Close()
        sys.exit()

        
    # Return time since the beginning of the run.
    # Note: this is a member function since start time is a member variable.
    def TimeSinceStart( self ):
        return TimeStamp()-self.starttime



# Python main function start here.
def main():
    if len(sys.argv)<2:
        print('# Did not detect commandline argument. Try run it with --help to see usage.')
        
        #ll = LeidenLogger( ['./leidenlogger','--port','COM7:COM6','--freq','60:10','--timeout', '10','--channel','1:2:3:4:5:7:9:10:11:12:14:15','--prefix','run16_cooldown','--delta','0.01'] )
        #ll.Execute()
        #ll.Close()
        
    else:
        print('#', sys.argv )
        ll = LeidenLogger( sys.argv )
        ll.Execute()
        ll.Close()

        
if __name__== "__main__":
    main()
    
    