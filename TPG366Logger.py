import serial

LINE_TERMINATION = "\x0D" + "\x0A" # Carriage Return + Line Feed

class TPG(object):
    # The default baud is 9600(?)
    def __init__(self, serialPort, baud=9600, debug=False):
        self.debug = debug
        try:
            self.connection = serial.Serial(serialPort, baudrate=baud, timeout=0.05)
        except:
            raise Exception('Error occurs during init')

    def debugMessage(self, message):
        if self.debug: print(repr(message))

    def write(self, what):
        self.debugMessage(what.encode())
        self.connection.write(what.encode())

    def readPressure(self, channel):
        check = self.send('PR{number}'.format(number = channel) + LINE_TERMINATION)
        response = None
        # ACQ: Positive feedback for data transmission request
        #print(check)
        if check == [b'\x06\r\n']:
            response = self.send('\x05')
            if response == [b'\x15\r\n']:
                print('Negative feedback from the machine. Data transmission request is rejected. Pleas check the input command')
            else:
                response = str(response)[5:-6]
                if response[0] == '+':
                    response = eval(response)
                else:
                    raise NegativePressureError()
        # NAK: Negative feedback for data transmission request
        if check == [b'\x15\r\n']:
            print('Negative feedback from the machine. Data transmission request is rejected. Pleas check the input command')
        # Unknown problems: Neither ACQ or NAK is reported.
        if check != [b'\x06\r\n'] and check != [b'\x15\r\n']:
            print('Unknown problems: Neither ACQ or NAK is reported. Please check hardware since this machine sometimes havs connection problems')
        
        # Enquire the data if the error emerges by sending 'ENQ'

        return response

    def send(self, what):
        self.write(what)
        response = self.connection.readlines()
        return response

class NegativePressureError():
    pass