#!/usr/bin/python3

import sys
import signal
import getopt
import time
import datetime
import LakeShoreController as LSC
import PfeifferGauge as PF

def Now():
    return datetime.datetime.now()

def TimeStamp():
    return Now().timestamp()

def TimeSince( t1, format='d' ):
    return int( TimeStamp() - t1 )

def PrintTimeStamp( file=sys.stdout ):
    print("#", TimeStamp(),' : ',Now(), file=file)

def PrintT( Dict, *, file=sys.stdout ):
    for key in Dict:
        if key == list(Dict.items())[0][0]:
            print( '%d' % Dict[key], end=", ", file=file )
        elif key == list(Dict.items())[-1][0]:
            print( '%e' % Dict[key], file=file )
        else:
            print( '%e' % Dict[key], end=", ", file=file )

def MaxChange(P2, P1, intv, delta):
    for key in P2:
        if key=='ts':
            if P2[key]-P1[key]>intv:
                return True
        else:
            change = P2[key]-P1[key]
            frac = change / P1[key]
            if frac>delta or frac<-delta:
                return True
    return False
            
    
# ===============================================
# Configure commandline parameters
# ===============================================

# Default serial port for making connection to LakeShore temperature controller
LSPort = "COM7"

# Default serial port for making connection to Pfeiffer TPG366 Gauge
PFPort = "COM6"

# Channels to record data. It should be a list of numbers between 1 to 16.
LSChannels = []

# AutoScan and maximum inactive time to turn on autoscan
LSAutoScan = True
LSTimeout = 10*60

# Interval in seconds between successive temperature readings while waiting for equilibrium
Interval = 60

# 
Delta = 0.01

# Output file and prefix.
# Output will be the direct and exact output filename without the .txt suffix.
# Prefix will also have the date and time information appended.
prefix = ""


# Obtain the commandline options and arguments.
# Setpoints will be the arguments which are specified in the end
opts, Setpoints = getopt.getopt( sys.argv[1:], "h",["channels=","timeout=","delta=","lsport=","pfport=","prefix=","freq=","help"] )

# Iterate through the commandline options to set the parameters.
for opt, arg in opts:

    if opt == "--prefix":
        prefix = arg+"_"+time.strftime('%Y%m%d')+"_"+time.strftime('%H%M%S')
        # If prefix is used instead, then append formated date and time to the prefix.    
    if opt in ("--delta"):
        Delta = float(arg)
        # maximum change of temperature in mK per min at equilibrium
    if opt in ("--freq"):
        Interval = int(arg)
        # The time in seconds between successive readings while waiting for equilibrium.

    if opt in ("--lsport"):
        LSPort = arg
        # USB/serial port for LakeShore
    if opt in ("--channels"):
        LSChannels = arg.split(':')
        # multiple channels separated by : as a whole single string
    if opt in ("--timeout"):
        LSTimeout = int(arg)*60
        # Maximum dwell time at a setpoint in minutes.

    if opt in ("--pfport"):
        PFPort = arg
        # USB/serial port for LakeShore
        
    if opt in ("-h","--help"):
        print("usage: "+sys.argv[0]+" [options optional_parameter]\n")
        print("options:\n")
        print("\t--prefix foo\t set the prefix of output filename to be foo_yyyymmdd_hhmmss.")
        print("\t            \t Three files with suffixes _pres, _temp and _liqlevel will be created.")
        print("\t--delta  foo\t record data when reading differs by more than foo (fraction) from previous reading.")
        print("\t--freq   foo\t interval in seconds between successive readings.\n")
        
        print("\t--lsport foo\t\t (LakeShore) use the specified serial port for LakeShore connection.")
        print("\t--channels L1:L2:L3\t (LakeShore) enable channel L1, L2, L3 for data taking. Note the colon as delimiter.")
        print("\t--timeout T\t\t (LakeShore) after T min of inactivity, autoscan will be turned on.\n")
        
        print("\t-h/--help \t display help message.\n")
        exit()


# ===============================================================
# Open the output files and write file headers.
# ===============================================================

FilePressure    = None
FileTemperature = None
#FileputLiqlevel = open( prefix+"_liqlevel.txt", "w")

if prefix=="":
    FileTemperature = sys.stdout
    FilePressure    = sys.stdout
    
else:
    FileTemperature = open( prefix+"_temp.txt", "w", buffering=1)
    FilePressure    = open( prefix+"_pres.txt", "w", buffering=1)

PrintTimeStamp( file = FileTemperature )
PrintTimeStamp( file = FilePressure )
print("# time since start", end='', file=FileTemperature)
for c in LSChannels:
    print(", channel "+c, end='', file=FileTemperature)
print('', file=FileTemperature)

# Record starting time as origin of time
StartTimeOffset = TimeStamp();


# ===============================================================
# Establish connection to the controller and configure parameters.
# ===============================================================

# LakeShore

print( "# Opening serial port %s for LakeShore controller" % LSPort )
controller = None
try:
    controller = LSC.LakeShoreController( LSPort )
except:
    exit(0)
    
LSPrevChannel = controller.GetCurrentChannel()
print( "# Current LakeShore scanner channel is", LSPrevChannel)

LSLastActivity = TimeStamp()
LSPrevReading = LSLastActivity-2*Interval
    # set the time of previous reading to be past to make sure a reading when first running the program

# Temperature dictionary
T1 = {}

# Pfeiffer

print( "# Opening serial port %s for Pfeiffer TPG366 gauge controller" % PFPort )
gauge = None
try:
    gauge = PF.PfeifferGauge( PFPort )
except:
    print('# Failed to open serial port for Pfeffer gauge controller...')
    controller.close()
    exit(0)

PFPrevReading = TimeStamp()-2*Interval

# Pressure dictionary
P1 = {}
#P1['ts'] = TimeStamp()
P1['ts'] = TimeSince( StartTimeOffset )
for c in range(1,7):
    P1['%d' % c] = gauge.readPressure(c)

P2 = {}

def handler(signum, frame):
    
    print('# Interruption signal detected. Exitting...')
    
    controller.close()
    gauge.close()
    
    FileTemperature.close()
    FilePressure.close()
    
    sys.exit()

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGBREAK, handler)

while True:
    # If autoscan is enabled, then go through the channels for temperature reading.
    # obtain LakeShore temperature readings:
    
    # first determine channel has been manually changed or not.
    # obviously, if channel has been manually changed, then autoscan shoud be turned off
    # and the time of last activity should be updated.

    if controller.GetCurrentChannel() != LSPrevChannel:
        print("# Manual activity detected in LakeShore controller.", end='')
        if LSAutoScan==True:
            PrintTimeStamp()
            print("# Turning off autoscan.")
            LSAutoScan = False
        LSLastActivity = TimeStamp()
        LSPrevChannel = controller.GetCurrentChannel()
        print("")

    # Next, determine the inactive time to see if autoscan should be turned back on
    if LSAutoScan==False and TimeStamp()-LSLastActivity>LSTimeout:
        LSAutoScan = True
        LSPrevChannel = controller.GetCurrentChannel()
        PrintTimeStamp()
        print("# Inactive for %d minutes. Turning on autoscan." % LSTimeout)

    if LSAutoScan==True and TimeStamp() - LSPrevReading > Interval:
        #print('# AutoScanning..')
        T1['ts'] = TimeSince( StartTimeOffset )
        LSPrevReading = TimeStamp()
        for c in LSChannels:
            #print('# (AutoScan) Reading channel', c)
            if controller.GetCurrentChannel()!=LSPrevChannel:
                LSAutoScan = False
                break
            T1[c] = controller.ReadKelvin( c )
            LSPrevChannel = controller.GetCurrentChannel()

        if LSAutoScan==True:
            PrintT( T1, file=FileTemperature)

            
    # Take care of the Pfeiffer pressure gauge
        
    P2['ts'] = TimeSince( StartTimeOffset)
    #P2['ts'] = TimeStamp()
    for c in range(1,7):
        P2['%d' % c] = gauge.readPressure(c)

    #print(P1,P2)
    if MaxChange(P2, P1, Interval, Delta)==True:
        #print(P1,P2)
        PrintT( P2, file=FilePressure)
        for key in P2:
            P1[key] = 1*P2[key]
        # update previous reading

    #time.sleep(1)

#    except:
#        print('# Interruption exception detected. Exitting...')
#        controller.close()
#        FileTemperature.close()
#        exit()

FileTemperature.close()
FilePressure.close()
controller.close()
gauge.close()
exit()