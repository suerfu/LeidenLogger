# written by B. Suerfu on June 25, 2021
# contact: suerfu@berkeley.edu

# This is a script to merge different data files of the same run.
# Multiple log files will be generated when the run is interrupted and the logger is restarted.
# For convenience, the time in each log file is referenced to the beginning of the program, but not the start of the run.
# This script will read the different log files and apply a time offset to all time fields to generate a single log file.
# It works by
# 1) sort the input files based on the timestamp ( which should be present on the first line with preceding '#' )
# 2) the first in the run, then it is copied directly without modifications.
# 3) the content of the second file and on forth will be copied with a time offset
#    the time offset is determined from the difference of the timestamps in the two log files.
#    by convention, all variables of interest are in the float format (with e or . present) while time is integer in second
#    when writing the output, the offset only applies to integer fields and thus only applies to time.
#    this script can be used for all of pressure, temperature and liquid level outputs.

# Note: this file cannot process files of different variables at the same time (e.g. pressure and temperature).

import sys
import pandas as pd

# Function to get the time stamp from the input file.
# The format of the file should always be that the beginning is # + timestamp

def GetTimeStampFromFile( filename ):
    with open( filename, 'r') as f:
        for n,l in enumerate(f):
            if n==0:
                return float(l.replace('#',''))
    print( filename + ' does not have the right format.')
    print( 'File should begin with # + timestamp.')
    return None

# Check if files to be merged have specified through commandline.
                
if len(sys.argv)==1:
    print('\nUsage: ' + sys.argv[0] + ' file0 file1 ...\n' )
    print('file0 file1, etc. are files of the same type to be merged.\n')
    sys.exit()

    
# Alias to the list of files to be processed.
files = sys.argv[1:]

# Timestamps of each file specified by the commandline.
timestamps = [GetTimeStampFromFile(i) for i in sys.argv[1:]]

# Dictionary structure that uses the timestamp as key and filename as value.
# It's easier to go through in chronological order in this way
dict_timestamp = {}
for f in files:
    dict_timestamp[ str(GetTimeStampFromFile(f)) ] = f

    
global_timestamp = 0


with open( 'merge.txt', 'w') as Output:
    
    # Iterate over all files.
    for n,timestamp in enumerate( sorted(dict_timestamp.keys()) ):
        
        # Get the time offset from the difference of timestamps
        offset = float(timestamp) - global_timestamp
        
        print('Processing '+dict_timestamp[timestamp] +' timestamp: ' + timestamp + ' offset: %d' % offset)
            
        # If the file is first in chronological order, then keep its content.
        if n==0:
            with open( dict_timestamp[timestamp],'r') as Input:
                Output.write( Input.read() )
                global_timestamp = float(timestamp)
                Input.close()
            
        # If not, then read the file into a pandas data structure and dump the output with time offset.
        else:
            with open( dict_timestamp[timestamp],'r') as Input:
                
                for l in Input.readlines():
                    
                    # Skip empty lines/meaningless lines
                    # Rows containing data has at least two columns (time + variable0)
                    if len(l) < 2:
                        continue
                    
                    # Skip comments
                    # If # is not found, it is not a comment.
                    if l.find('#') < 0:
                        
                        # Iterate over each column
                        for n, word in enumerate( l.split(',') ):
                            
                            # If word contains e or ., it is a float, not timestamp
                            # In this case, simply print it to file.
                            if word.find('e') >= 0 or word.find('.') >= 0:
                                
                                # If it is beginning of line, do not print the comma
                                if n==0:
                                    print( float(word), end='', file=Output )
                                
                                # If not begin of line, then print the delimiting comma in the front.
                                else:
                                    print( ', %f' % float(word), end='', file=Output )
                            
                            # If word doesn't contain e or ., it is a timestamp.
                            # Apply the offset and print.
                            else:
                                if n==0:
                                    print( '%d' % (int(word)+offset), end='', file=Output )
                                else:
                                    print( ', %d' % (int(word)+offset), end='', file=Output )
                        
                        # After each row, print a line feed.
                        print('\n',end='', file=Output)
