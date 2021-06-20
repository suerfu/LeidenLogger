# Leiden Fridge Slow Control

This repository contains code for two programs: LeidenLogger and LeidenSequencer.

## LeidenLogger

LeidenLogger is used to monitor and record the status (temperatures, pressure and liquid helium level) of the Leiden fridge in the McKinsey Lab. LeidenLogger will create three different data files recording the temperatures, pressures and liquid helium levels separately. This is because these three parameters could be potentially changing with rather different time characteristics. The sampling intervals can be configured separately through commandline argument.

Normally, LeidenLogger will scan the LakeShore scanners through enabled channels. When a user physically changes the scanner channel, LeidenLogger will release its control over the LakeShore temperature controller and instead updates only the channel user is looking at physically at the moment. When certain time has elapsed without physical activity, then LeidenLogger will regain control of the LakeShore controller and enters the autoscan mode. The duration of inactivity can be configured through commandline argument.

### LeidenLogger Output

The output file containing temperature data (file with suffic _temp.txt) contains 3 x No. of enabled channels. The columns are in order time of sampling in seconds, temperature read out from the LakeShore controller in Kelvin, and resistance of the thermometer. This basic structure is then repeated for all enabled channels as additional columns. The resistance is also recorded in case the temperature is outside calibration range.

The output file for pressure data (suffix _pres.txt) contains 7 columns: first column is time since begin of run, and the other six columns are the six channels of the Pfeiffer Gauge controller. Note: the interpretation of the 6 channels are subject to the actual hardware configuration. It can be changed at any moment by a different connection scheme. For the true interpretation, always refer to the actual configuration.

The output file for liquid level (suffix _liqlev.txt) contains 3 columns: first column is time since start, and the other two liquid helium and liquid nitrogen levels. The unit is cm by default. Note that this unit can be potentially changed by reconfiguring the hardware to inches or percent.

### Usage

The program is executed by typing the following in the commandline terminal:
```
python LeidenLogger.py [options] [parameters]
```
#### Common Parameters
* --help: print usage and help messages
* --port A:B:C Specifies the serial port used for connecting to the hardware. The orders are A-LakeShore, B-Pfeiffer, C-CryoMagnetics. All these devices use USB-emulated serial ports. On Windows machines, serial port is usually COMx where x is a digit. To see what ports are enabled, on Windows PC, one should go into the Devices-COM ports. On Linux PC, one can plug the USB and see the systems hardware message by running dmesg.
* --freq foo:bar:baz set the sampling frequency (time interval between sampling in seconds) for LakeShore temperature controller (foo), Pfeiffer gauge controller (bar), and CryoMagnetics (baz).

#### Configuring Output
* --prefix foo: this option will set the output files to be foo_yyyymmdd_hhmmss_temp.txt for temperatures (_pres.txt and _liqlev.txt for pressures and liquid level, respectively)

#### Configuring LakeShore Temperature Controller
* --channel foo:bar:baz:... specified channels will be enabled for data recording.
* --timeout foo: When there has been no user activity for foo minutes on the LakeShore controller, the program regains control and enters autoscan mode to periodically scan through all enabled channels.

#### Configuring Pfeiffer Gauge
* --delta foo: when pressure change exceeds foo (in fraction), the pressures are recorded even before sampling time has exceeded.

#### Configuring the Server
* --no-server: No server file is written.
* --server-file foo.txt: Sets the output filename for the fridge status. This file is supposed to be read by the server program. The default name is leiden_status.txt. Note that if one specifies a different file, they must change the server program as well.

## LeidenSequencer

LeidenSequencer is used to set sample heater to a series of specified setpoints and records the equilibrium temperature of the sample. It is mainly used to measure the sample's thermal conductance and heat load.

### Usage

LeidenSequencer is run by typing the following in the commandline prompt:
```
python LeidenSequencer [opt] [arg] p1 p2 p3 ...
```
This command will start the LeidenSequencer and set the sample heater power to be p1, p2, p3 (Watt) in sequence. To configure the program, the following options are available:

#### Establishing Connection and Enabling Channels
* -p / --port: Speficies the serial port (COMx on Windows, ttyX) to communicate to LakeShore controller.
* -c / --channels 1:2:3:etc Record the transient temperatures of channels. Different channels are separated by :. The range of channels are 1-16.
* -s / --sample s: Set the sample channel. While all enabled channels under --channels will be monitored, the temperature of the sample channel is used to determine equilibrium. 
* -R foo: Sets the resistance of the sample heater. This resistance is needed in getting the right current range and power output.
* --freq foo: Sampling interval in seconds (yes, it is in second, though it's called frequency). 

#### Configuring the Output
* -o / --output foo: Set the output file to be foo.txt. The transient temperatures are recorded in foo.log.
*  --prefix foo: Instead of setting the output name directly, prefix will set only file prefix. In the actual filename, date and time will be appended.

#### Equilibrium Criteria
* -d / -dTdt foo: The program will record in the output file the final equilibrium temperature. The judgement criteria is either specified maximum dwell time has elapsed, or when the temperate rate of change (in Kelvin per min) is smaller than the specified value.
* --timeout foo: Sets the maximum dwell time at each power setpoint.
* --wait foo: Sets the minimum dwell time at each power setpoint. Note: if this is too small, the program might judge that equilibrium has obtained where the system has not had enough time to respond to power input.
