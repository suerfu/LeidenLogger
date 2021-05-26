#!/usr/bin/python3

import sys
import getopt
import time
import datetime
from LakeShoreController import LakeShoreController

def Now():
    return datetime.datetime.now()

def TimeStamp():
    return Now().timestamp()

def TimeSince( t1, format='d' ):
    return int( TimeStamp() - t1 )

def PrintTimeStamp( file=sys.stdout ):
    print("#",Now(), file=file)

def PrintT( Dict, *, file=sys.stdout ):
    for key in Dict:
        if key == list(Dict.items())[-1][0]:
            print( Dict[key], file=file )
        else:
            print( Dict[key], end=", ", file=file)


class LeidenSequencer( object ):
    
    def __init__( self, argv ):
        print("# creating...")
        
        # LakeShore controller object
        self.controller = None
        
        # Default serial port for making the connection
        self.Port = "COM7"

        # Channels to record data. It should be a list of numbers between 1 to 16.
        self.Channels = []
        self.SampleChannel = -1

        # Resistance of the sample heater in ohm
        self.Resistance = 10

        # Default timeout parameter in minutes
        self.Timeout = 60

        # Interval in seconds between successive temperature readings while waiting for equilibrium
        self.Interval = 60

        # Maximum change required in mK/min for a stable datapoint
        self.dTdt = 1

        # Output file and prefix.
        # Output will be the direct and exact output filename without the .txt suffix.
        # Prefix will also have the date and time information appended.
        self.prefix = "output"
        temp = self.prefix+"_"+time.strftime('%Y%m%d')+"_"+time.strftime('%H%M%S') 
        self.Log = temp+'.log'
        self.Output = temp+'.txt'

        # system output
        self.Sysout = [sys.stdout]
        
        self.ConfigOpt( argv )
        self.SetupSignalHandler()
        
        # Temperature dictionaries 1 and 2.
        self.T1 = {}
        self.T2 = {}
        
        
    def Execute( self ):
        
        self.Book()
        self.PrintConfig()
        self.ConfigLakeShore()
        
        # Record starting time as origin of time
        self.StartTimeOffset = TimeStamp();
        for f in self.Sysout:
            print('# [', self.StartTimeOffset,']', file = f )
        
        self.Sequence()
        
    # Configure commandline parameters        
    def ConfigOpt( self, argv):
        # Obtain the commandline options and arguments.
        # Setpoints will be the arguments which are specified in the end
        opts, self.Setpoints = getopt.getopt( argv[1:], "c:t:d:R:p:o:hs:",[ "timeout=", "dTdt=", "port=", "prefix=", "output=", "freq=", "sample=", "help" ] )

        # Iterate through the commandline options to set the parameters.
        for opt, arg in opts:

            if opt in ("-c","--channels"):
                self.Channels = arg.split(':')
                # multiple channels separated by : as a whole single string

            if opt in ("-d","--dTdt"):
                self.dTdt = float(arg)
                # maximum change of temperature in mK per min at equilibrium

            if opt in ("-o","--output"):
                self.Output = arg+".txt"
                self.Log = arg+".log"
                # If output is specified, then set the filenames directly.

            if opt == "--prefix":
                foo = arg+"_"+time.strftime('%Y%m%d')+"_"+time.strftime('%H%M%S')
                self.Output = foo+".txt"
                self.Log = foo+".log"
                # If prefix is used instead, then append formated date and time to the prefix.

            if opt in ("-p","--port"):
                self.Port = arg
                # USB/serial port

            if opt == "-R":
                self.Resistance = float(arg)
                # Heater resistance

            if opt in ("-s", "--sample"):
                self.SampleChannel = arg
                # The channel which is used to judge stabilization

            if opt in ("--freq"):
                self.Interval = int(arg)
                # The time in seconds between successive readings while waiting for equilibrium.

            if opt in ("-t", "--timeout"):
                self.Timeout = int(arg)
                # Maximum dwell time at a setpoint in minutes.

            if opt in ("-h","--help"):
                print("usage: " + argv[0] + " [options optional_parameter] X1 [X2, X3, ...]\n")
                print("LakeShore controller will go through heater output power through X1 [,X2,X3,...] W and record the temperature when stable.\n")
                print("options:\n")
                print("\t-c/--channels L1:L2:L3\t\t enable channel L1, L2, L3 for data taking. Note the colon as delimiter.\n")
                print("\t-d/--dTdt foo\t set the maximum allowed rate of temperature change for a stable datapoint to be foo mK/min.\n")
                print("\t--freq foo\t Interval in seconds between successive reading while waiting for equilibrium.\n")
                print("\t-h/--help \t display help message.\n")
                print("\t-o/--output foo\t set the output filename to be foo.txt. Default is output_yyyymmdd_hhmmss.txt.\n")
                print("\t--prefix foo\t set the prefix of output filename to be foo_yyyymmdd_hhmmss.txt.\n")
                print("\t-p/--port foo\t use the specified serial port (default is COM7 based on the current USB configuration).\n")
                print("\t-R foo\t set the sample heater resistance. Default is 10 ohms.\n")
                print("\t-s foo\t set the sample channel to foo (default is last enabled channel). Its temperature is used as stabilization criteria.\n")
                print("\t-t/--timeout T\t set the maximum wait time for temperature to stablize to be T min.\n")
                sys.exit()
                
                
    def Book( self ):
        # If sample channel is not specified, then use the last enabled channel as sample channel.
        if self.SampleChannel==-1:
            self.SampleChannel = self.Channels[-1]

        if self.SampleChannel not in self.Channels:
            for f in self.Sysout:
                print( '# Error: sample channel',self.SampleChannel,'is not in enabled channel', file=f )
                print( '# Using the last channel.', file=f )
            self.SampleChannel = self.Channels[-1]
            
        # Configure output files
        self.OutputFile = open( self.Output, "w", buffering = 1)
        print( "#", TimeStamp(), file = self.OutputFile )
        print( "# Time since start (s), Power (W)", end='', file = self.OutputFile)
        for i in self.Channels:
              print(', T%s (K)' % i, end='', file = self.OutputFile)
        print( file = self.OutputFile)
        print( '# Using channel %s as the sample channel.\n' % self.SampleChannel, file = self.OutputFile)

        
        self.LogFile = open( self.Log, "w", buffering = 1)
        self.Sysout.append( self.LogFile )

        
    def PrintConfig( self ):
        # Print configuration information.
        for f in self.Sysout:
            print( "# File %s and %s will be used for  data output and logging." % (self.Output,self.Log) , file=f )
            print( "# Port %s will be used to access the controller." % self.Port , file=f )
            print( "# Channels enabled: ", end="" , file=f )
            print( self.Channels , file=f )
            print( "# Sample channel is %s" % self.SampleChannel , file=f )
            print( "# Temperature is recorded either after %d minutes or when the rate of change is less than %.2f K/min" % (self.Timeout, self.dTdt) , file=f )
            print( "# The resistance of the sample heater is set to be %.2f ohm." % self.Resistance , file=f )
            print( "# Power setpoints (in W):", end=" " , file=f )
            print( self.Setpoints , file=f )
            print( '', file=f )


    # Establish connection to the controller and configure parameters.
    def ConfigLakeShore( self ):
        for f in self.Sysout:
            print( "# Configuring LakeShore Controller...", file=f )
        try:
            self.controller = LakeShoreController( self.Port )
        except:
            for f in self.Sysout:
                print( "# Unable to configuring LakeShore Controller...", file=f )
            self.Close()
            sys.exit()

        for f in self.Sysout:
            print( "# Adding log file...", file=f )
        self.controller.AddLogFile( self.LogFile )

        # Configure the resistance of the controller
        self.controller.SetHeaterResistance( self.Resistance )


    # Iterate through the specified power setpoints
    # Set the heater output power
    # Wait for stabilization
    # Record the temperature.
    def Sequence( self ):

        for setpoint in self.Setpoints:
            power = float(setpoint)
            self.controller.SetHeaterPower( power )

            #for f in Sysout:
                # PrintTimeStamp( file=f )
                # print( "# Setting heater power to %e Watt" % power, file=f )

            self.T1['ts'] = TimeSince( self.StartTimeOffset )
            self.T1['pw'] = power
            
            self.ReadTemperature( self.T1 )

            for f in self.Sysout:
                PrintT( self.T1, file=f )
            time.sleep( self.Interval )

            while True:
                self.T2['ts'] = TimeSince( self.StartTimeOffset)
                self.T2['pw'] = power

                # Iterate through the enabled channels to record temperature
                self.ReadTemperature( self.T2 )
                for f in self.Sysout:
                    PrintT( self.T2, file=f )

                # Check if rate of change is small enough
                rate = self.GetRate( self.SampleChannel, self.T2, self.T1 )
                if rate < self.dTdt:
                    for f in self.Sysout:
                        print('# Stabilized: dT/dt = %f K/min, rate of change is smaller than %f' % ( rate, self.dTdt ), file=f )
                    break
                    
                # Check for timeout
                elif self.SequencerTimeout()==True:
                    for f in self.Sysout:
                        print('#', Now(), 'Timeout: %d s - %d s > %d min' % (self.T2['ts'],self.T1['ts'], self.Timeout), file=f );
                    break

                # If not stabilized yet, wait for the specified interval and then update T1
                else:
                    time.sleep( self.Interval )
                    self.UpdateTemperature( self.T1, self.T2 )

            self.T1['ts'] = TimeSince( self.StartTimeOffset )
            self.ReadTemperature( self.T1 )
            # need to write temperature output here!!!
            PrintT( self.T1, file = self.OutputFile)
    
    
    # Check if maximum time between setpoints have elapsed.
    def SequencerTimeout( self ):
        return self.T2['ts']-self.T1['ts'] > self.Timeout*60
    
    
    # Calculate rate of temperature change.
    def GetRate( self, Channel, T2, T1 ):
        dT = abs(T2[Channel] - T1[Channel])
        dt = (T2['ts'] - T1['ts'])/60
        return dT/dt    
    
    # Function to update current temperature reading
    def ReadTemperature( self, T, Navg=10 ):
        for ch in self.Channels:
            # switch scanner to the channel and wait for reading to stabilize
            self.controller.SetChannel( ch )
            self.controller.wait(5)
            
            # perform successive Navg readings and return the average
            T[ch] = 0 
            for i in range( 1, Navg ):
                T[ch] += self.controller.ReadKelvin( ch )
            
            T[ch] /= Navg
            
    def UpdateTemperature( self, Dest, Source):
        for key in Dest:
            Dest[key] = Source[key]
    
    
    # Terminate the program.
    def Close( self ):
        if self.controller:
            self.controller.SetHeaterPower( 0.0 )
            self.controller.close()
            self.controller = None

        self.OutputFile.close()
        self.LogFile.close()

    def SetupSignalHandler( self ):
        signal.signal( signal.SIGINT, self.Terminate )
        signal.signal( signal.SIGBREAK, self.Terminate )
        
    def Terminate( self, signum, frame ):
        print('# LeidenLogger: interruption signal detected. Preparing to exit...')
        
        # If user signals program end, close connection to devices and write output to files.
        self.Close()
        sys.exit()

        
        
# Python main function start here.
def main():
    print('#', sys.argv )
    seq = LeidenSequencer( sys.argv )
    if seq:
        seq.Execute()
        seq.Close()
    else:
        print('# Failed to create sequencer object.')
    
    
if __name__== "__main__":
    main()