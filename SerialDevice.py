# May 24, 2021
# Created by Burkhant Suerfu
# suerfu@berkeley.edu

# This is a parent class for handling serial devices.
# It implements some common functions related to serial communication
# such as open and close port, read and write, etc.

# Serial parameters can include:
# Baudrate,
# No. of data bit, start bit, and stop bit
# Parity: even, odd, none


import serial
import sys
import time


class SerialDevice(object):

    # Constructor
    # Use named arguments for configurations with default settings.
    # logs is a list of file objects for recording the output or for debugging
    # The argument term is termination character for a sentence. By default it is carriage return + line feed.
    def __init__(self, port, *, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=0.05, term='\r\n', logs=[sys.stdout]):
        
        # Attempt to open the serial connection with the default/specified parameters
        self.term = term
        self.logfiles = logs
        
        print("# Creating SerialDevice at", port)
        
        try:
            self.connection = serial.Serial(port = port,
                                            baudrate = baudrate,
                                            bytesize = bytesize,
                                            parity = parity,
                                            stopbits = stopbits,
                                            timeout = timeout )
            # termination characters that should be removed from reply strings or should be appended to strings being sent out.
            
        except serial.SerialException:
            self.log( '# Serial port', port, 'not found.' )
            raise
        except:
            self.log( '# Failed to open serial port', port )
            raise
        else:
            self.log('# Opened serial port', port )
            self.reset_input();
            
    # Check status of serial port
    def is_open(self):
        return self.connection.is_open
    
    # Close the port
    def close(self):
        self.connection.close()
        self.log('# Serial port closed' )
    
    # Clear the input buffer
    def reset_input(self):
        self.connection.reset_input_buffer()
    
    # Reconfigure the log file to be a single log file
    def SetLogFile( self, l):
        self.logfiles = [l]
    
    # Add additional location for logging   
    def AddLogFile( self, l):
        if l not in self.logfiles:
            self.logfiles.append(l)
    
    # Read the serial port
    # Note this function will read the input buffer until the termination character
    # After the read, the delimiter is removed from the line.
    def read(self, char=None, size=None):
        if char==None:
            char = self.term
        response = self.connection.read_until( char, size )
        response = response.decode('ascii')
        for c in char:
            response = response.replace( char,'')
        return response

    # Send command through the serial port to the device
    # If wait is specified, function will pause for the specified seconds for proper response.
    def write(self, msg, *, wait=0 ):
        
        # Check if message has the desired termination or appending characters
        # If not, append to the message
        if msg.find( self.term )<0:
            msg += self.term
        
        # Send the command and return the number of bytes written
        reply = self.connection.write( msg.encode('ascii') )
        
        self.wait(wait)

        return reply
        
    # Wait for t seconds
    # Needed when serial device needs time for update.
    def wait(self, t):
        time.sleep(t)
        
        
    # log some output. This is a wrapper for python's print function except output is printed to all log destinations
    def log(self, *objects, sep=' ', end='\n' ):
        for f in self.logfiles:
            print( *objects, sep=sep, end=end, file=f)
            