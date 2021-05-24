#!/usr/bin/python3

import sys
import getopt
import time
import datetime
import LakeShoreController as LSC

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


# ===============================================
# Configure commandline parameters
# ===============================================

# Default serial port for making the connection
Port = "COM7"

# Channels to record data. It should be a list of numbers between 1 to 16.
Channels = []
SampleChannel = -1

# Resistance of the sample heater in ohm
Resistance = 10

# Default timeout parameter in minutes
Timeout = 60

# Interval in seconds between successive temperature readings while waiting for equilibrium
Interval = 60

# Maximum change required in mK/min for a stable datapoint
dTdt = 1

# Output file and prefix.
# Output will be the direct and exact output filename without the .txt suffix.
# Prefix will also have the date and time information appended.
prefix = "output"
temp = prefix+"_"+time.strftime('%Y%m%d')+"_"+time.strftime('%H%M%S') 
Log = temp+'.log'
Output = temp+'.txt'

# system output
Sysout = [sys.stdout]

# Obtain the commandline options and arguments.
# Setpoints will be the arguments which are specified in the end
opts, Setpoints = getopt.getopt( sys.argv[1:], "c:t:d:R:p:o:hs:",["timeout=","dTdt=","port=","prefix=","output=","freq=","sample=","help"] )

# Iterate through the commandline options to set the parameters.
for opt, arg in opts:

    if opt in ("-c","--channels"):
        Channels = arg.split(':')
        # multiple channels separated by : as a whole single string

    if opt in ("-d","--dTdt"):
        dTdt = float(arg)
        # maximum change of temperature in mK per min at equilibrium

    if opt in ("-o","--output"):
        Output = arg+".txt"
        Log = arg+".log"
        # If output is specified, then set the filenames directly.

    if opt == "--prefix":
        foo = arg+"_"+time.strftime('%Y%m%d')+"_"+time.strftime('%H%M%S')
        Output = foo+".txt"
        Log = foo+".log"
        # If prefix is used instead, then append formated date and time to the prefix.

    if opt in ("-p","--port"):
        Port = arg
        # USB/serial port

    if opt == "-R":
        Resistance = float(arg)
        # Heater resistance

    if opt in ("-s", "--sample"):
        SampleChannel = arg
        # The channel which is used to judge stabilization

    if opt in ("--freq"):
        Interval = int(arg)
        # The time in seconds between successive readings while waiting for equilibrium.

    if opt in ("-t", "--timeout"):
        Timeout = int(arg)
        # Maximum dwell time at a setpoint in minutes.

    if opt in ("-h","--help"):
        print("usage: "+sys.argv[0]+" [options optional_parameter] X1 [X2, X3, ...]\n")
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
        exit()

# If sample channel is not specified, then use the last enabled channel as sample channel.
if SampleChannel==-1:
    SampleChannel = Channels[-1]

if SampleChannel not in Channels:
    for f in Sysout:
        print( '# Error: sample channel',SampleChannel,'is not in Channels', file=f )
    exit( -1 )
# Configure output files

OutputFile = open( Output, "w")
LogFile = open( Log, "w")
Sysout.append( LogFile )

# Print configuration information.
for f in Sysout:
    PrintTimeStamp( file = f )
    print( "# File %s and %s will be used for  data output and logging." % (Output,Log) , file=f )
    print( "# Port %s will be used to access the controller." % Port , file=f )
    print( "# Channels enabled: ", end="" , file=f )
    print( Channels , file=f )
    print( "# Sample channel is %s" % SampleChannel , file=f )
    print( "# Temperature is recorded either after %d minutes or when the rate of change is less than %.2f mK/min" % (Timeout,dTdt) , file=f )
    print( "# The resistance of the sample heater is set to be %.2f ohm." % Resistance , file=f )
    print( "# Power setpoints (in W):", end=" " , file=f )
    print( Setpoints , file=f )
    print( '', file=f )

# Record starting time as origin of time
StartTimeOffset = TimeStamp();
for f in Sysout:
#    print( "\n", file=f )
    PrintTimeStamp( file=f )
    print( '', file=f )



# ===============================================================
# Establish connection to the controller and configure parameters.
# ===============================================================

for f in Sysout:
    print( "# Opening the serial port...", file=f )
controller = LSC.LakeShoreController( Port )

for f in Sysout:
    print( "# Adding log file...", file=f )
controller.AddLogFile( LogFile )

# Configure the resistance of the controller
controller.SetHeaterResistance( Resistance )


# Temperature dictionaries 1 and 2.
T1 = {}
T2 = {}

# Iterate through the specified power setpoints
# Set the heater output power
# Wait for stabilization
# Record the temperature.

for setpoint in Setpoints:
    
    power = float(setpoint)
    controller.SetHeaterPower( power )

    #for f in Sysout:
        # PrintTimeStamp( file=f )
        # print( "# Setting heater power to %e Watt" % power, file=f )

    T1['ts'] = TimeSince( StartTimeOffset )
    T1['pw'] = power
    for c in Channels:
        T1[c] = controller.ReadKelvin( c )

    for f in Sysout:
        PrintT( T1, file=f )
    time.sleep( Interval )

    while True:
        T2['ts'] = TimeSince( StartTimeOffset)
        T2['pw'] = power

        # Iterate through the enabled channels to record temperature
        for ch in Channels:
            T2[ch] = controller.ReadKelvin( ch )

        for f in Sysout:
            PrintT( T2, file=f )

        # First judge if time out
        if T2['ts']-T1['ts']>Timeout*60:
            #for f in Sysout:
                #print('# Timeout: current time is',Now(), file=f );
            break;

        # Check rate of temperature change.
        rate = abs(T2[SampleChannel] - T1[SampleChannel])
        rate /= (T2['ts'] - T1['ts'])/60
        if rate<dTdt:
            #for f in Sysout:
                #print('# Stabilized: rate of change is smaller than %f' % dTdt, file=f)
            break
        
        # If not stabilized yet, wait for the specified interval and then update T1
        time.sleep( Interval )
        for ch in Channels:
            T1[ch] = T2[ch]

    T1['ts'] = TimeSince( StartTimeOffset )
    for c in Channels:
        T1[c] = controller.ReadKelvin( c )
    
    print( power, end=' ', file=OutputFile)
    PrintT( T1, file=OutputFile )
    print( '', file=OutputFile )

controller.SetHeaterPower( 0.0 )
controller.close()

OutputFile.close()
LogFile.close()

exit()