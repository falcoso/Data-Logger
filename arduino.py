import serial
import logging as log
import struct
import numpy as np

class ArduinoBoard:
    """
    Wrapper Class to help simplify communications with an Arduino Board
    connected over a serial port.

    Parameters
    ----------
    port : str
        Port that the Arduino is connected to.
    baud : int
        baud rate of serial communications.
    timeout : int
        Connection timeout.

    Attributes
    ----------
    board : serial.Serial()
        Serial connection to Arduino.
    sample_no : int
        Number of samples in a frame.
    sample_freq : int
        Sampling Frequency.

    Public Methods
    ----------
    setup(self):
        Initialises connection with Arduino and gathers samples metadata.

    send_command(self, message):
        Sends the desired command to the Arduino.

    get_data(self):
        Reads data from the Arduino.
    """

    def __init__(self, port, baud, timeout):
        self.board = serial.Serial(port, baud, timeout=timeout)
        self.sample_no, self.sample_freq = self.setup()
        self.LED = 0  # current LED that is lit
        return

    def setup(self):
        """
        Initialises connection with Arduino and gathers samples metadata.
        """
        try:
            line = str(self.board.readline(), "utf-8")
        except UnicodeDecodeError:
            line = str(self.board.readline(), "utf-8")
        if "Setup Complete" not in line:
            raise RuntimeError("Unable to complete setup, recieved: {}".format(line))

        frame_len = str(self.board.readline(), "utf-8").split(":")
        frame_len = int(frame_len[-1])
        log.info("[+] Sample rate: {}".format(frame_len))
        sample_freq = str(self.board.readline(), "utf-8").split(":")
        sample_freq = int(sample_freq[-1])
        log.info("[+] Sample freq: {}".format(sample_freq))
        return frame_len, sample_freq

    def send_command(self, message):
        """
        Sends the desired command to the Arduino
        """
        log.debug("send_command input: {}".format(message))
        message_dict = {"Standby": '1',
                        "Send Data": '2',
                        "LED1": '3',
                        "LED2": '4',
                        "LED3": '5',
                        "LED4": '6',
                        "LED7": '7',
                        "Sample 4k": '0',
                        "Sample 7k": '8',
                        "Sample 9k": '9',
                        "Frame 256": 'a',
                        "Frame 512": 'b',
                        "Frame 800": 'c',
                        "Frame 1024": 'd'}

        inverted_dict = dict([(label, key) for key, label in message_dict.items()])

        if isinstance(message, int):
            if message > 9:
                print("[+] ERROR: Message not configured on Arduino")
                return
            message = str(message)
            message_label = inverted_dict[message]
        elif len(message) == 1:
            try:
                if int(message) > 9:
                    print("[+] ERROR: Message not configured on Arduino")
                    return
            except TypeError:
                print("[+] ERROR: Message not configured on Arduino")
                return
            message_label = inverted_dict[message]

        elif message in message_dict.keys():
            message_label = message
            message = message_dict[message]
        else:
            print("[+] ERROR: Message not configured on Arduino")
            return

        # send message
        self.board.write(message.encode("utf-8"))
        log.info("[+] Message Sent: {} ({})".format(message_label, message))
        line = self.board.readline()
        # check confirmation:
        log.info("[+] Response: {}".format(line))
        try:
            line = str(line, "utf-8")
            if message not in line:
                print("[+] ERROR: Unable to acknowledge message:{}".format(line))
        except UnicodeDecodeError:
            pass
        return

    def get_data(self):
        """Reads data from the Arduino"""
        data = self.board.read(self.sample_no)
        try:
            data = np.array(struct.unpack('b'*self.sample_no, data))
        except struct.error as e:
            print(data)
            raise e
        return data
