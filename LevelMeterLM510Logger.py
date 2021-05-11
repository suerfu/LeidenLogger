import serial

LINE_TERMINATION = "\x0D" + "\x0A" # Carriage Return + Line Feed

class LevelMeter(object):
    # The default baud is 9600
    def __init__(self, serialPort, baud=9600, debug=False):
        self.debug = debug
        try:
            self.connection = serial.Serial(serialPort, baudrate=baud, timeout=0.05)
        except:
            raise Exception('Error occurs during init. Please physically reconnect the USB cable.')

    def debugMessage(self, message):
        if self.debug: print(repr(message))

    def write(self, what):
        self.debugMessage(what.encode())
        self.connection.write(what.encode())

    def readLevel(self, channel):
        response = self.send('MEAS? ' + str(channel))
        string = str(response)
        stringlist = string.split(', ')
        measurement = 0
        for element in stringlist:
            if element.find('cm') != -1:
                measurement = eval((element.replace("b'","").replace(" cm","").replace("\\",""))[:-5])
        return measurement

    def send(self, what):
        self.write(what + LINE_TERMINATION)
        response = self.connection.readlines()
        return response

