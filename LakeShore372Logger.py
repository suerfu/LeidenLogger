import serial

LINE_TERMINATION = "\x0D" + "\x0A" # Carriage Return + Line Feed

class LakeShore(object):
    # The default baud is 57600
    def __init__(self, serialPort, baud=57600, debug=False):
        self.switch = 1 
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

    def readTemp(self, channel, pause = 1):
        previous_channel = self.send('SCAN?')
        if previous_channel == [b'\xb0\xb5,\xb0\r\x8a']:
            self.switch = 0
            print('Auto scanner is OFF, please switch to channel 6 to turn it on.')
        elif previous_channel == [b'\xb0\xb6,\xb0\r\x8a']:
            self.switch = 1
            print('Auto scanner is now ON.')
        if self.switch == 1:
        # Switch channel based on the previous channel   
            if pause == 1:
                self.send('SCAN ' + str(channel) + str(', 0'))
            if pause ==0:
                pass

        response = self.send('RDGK? ' + str(channel))
        # typical instance: [b'\xab\xb0\xae\xb0\xb0\xb0\xb0\xb0E\xab\xb0\xb0\r\x8a']
        string = str(response).replace('[]', '')
        raw_string = string
        # To remove the tail
        string = string[:-8]
        # To remove the head 
        string = string[7:]
        # To remove the rest '\xb' 
        string = string.replace('\\xb', '').replace('\\xae', '.').replace('E', '').replace('\\xab', '').replace('\\xad03','')
        if string == None:
            measurement = 0
        else: 
            try:
                measurement = eval(string)
            except:
                print(raw_string)
                measurement = 0
        return measurement


    def send(self, what):
        self.write(what + LINE_TERMINATION)
        response = self.connection.readlines()
        return response


