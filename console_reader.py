import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import sys
import serial
import logging as log
import struct
import copy


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
        message_dict = {"Sample 4k": '0',
                        "Standby": '1',
                        "Send Data": '2',
                        "LED1": '3',
                        "LED2": '4',
                        "LED3": '5',
                        "LED4": '6',
                        "LED7": '7',
                        "Sample 6k": '8',
                        "Sample 8k": '9'}

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
        log.debug(len(data))
        data = np.array(struct.unpack('b'*self.sample_no, data))
        return data


class SpectrumAnalyser:
    """
    Creates a Spectrum Analyser window which process data from an Arduino Board
    and plots it.

    Parameters
    ----------
    None

    Attributes
    ----------
    board : ArduinoBoard()
        Arduino from which data is gathered.
    sample_no : int
        Number of samples in a frame.
    sample_freq : int
        Sampling Frequency.
    win : KeyPressedWindow()
        Window to display plots.

    Public Methods
    --------------
    keyPressed(self, evt):
        Handles key pressed while the graphs are in focus. Sends the pressed
        command to the Arduino, and re-scales the axis if sampling frequency
        is changed.

    scale_plots(self):
        Scales the figures based on the current sampling frequency.

    align_music(self, freq):
        Scales the self.NOTES such that the given frequency is in range.

    tune(self, sp_data):
        Finds the closest frequency to a natural octave note from the input signal.

    set_plotdata(self, name, data_x, data_y):
        Sets the data for the give plot name.

    update(self):
        Gathers new data and updates all the plots.

    spectrogram_update(self, sp_data):
        Updates the spectrogram plot
    """
    def __init__(self):
        self.board = ArduinoBoard("/dev/ttyACM0", 115200, timeout=5)
        self.sample_no = self.board.sample_no
        self.sample_freq = self.board.sample_freq
        self.xscale = 1
        self.yscale = 1

        self.NOTES = np.array([440, 493.88, 523.25, 587.33, 659.25, 698.46, 783.99, 880])
        self.note_keys = ["A", "B", "C", "D", "E", "F", "G", "A+"]
        self.note_dict = dict([(freq, note) for freq, note in zip(self.NOTES, self.note_keys)])
        # tell Arduino to start sending data
        self.board.send_command("Send Data")

        # pyqtgraph stuff
        pg.setConfigOptions(antialias=True)
        self.traces = dict()
        self.app = QtGui.QApplication(sys.argv)
        self.win = KeyPressWindow(title='Spectrum Analyzer')
        self.win.setWindowTitle('Spectrum Analyzer')

        self.win.sigKeyPress.connect(self.keyPressed)

        self.waveform = self.win.addPlot(title='WAVEFORM', row=1, col=1,
                                         labels={'bottom': "Time (s)"})
        self.spectrum = self.win.addPlot(title='SPECTRUM', row=1, col=2,
                                         labels={'bottom': "Frequency (Hz)"})
        self.specgram = self.win.addPlot(title='SPECTROGRAM', row=2, col=1,
                                         colspan=2, labels={'bottom': "Frequency (Hz)"})

        self.img = pg.ImageItem()
        self.specgram.addItem(self.img)

        self.img_array = np.zeros((100, int(self.sample_no/2+1)))

        # bipolar colormap
        pos = np.array([0., 1., 0.5, 0.25, 0.75])
        color = np.array([[0, 255, 255, 255], [255, 255, 0, 255], [0, 0, 0, 255],
                          (0, 0, 255, 255), (255, 0, 0, 255)], dtype=np.ubyte)
        cmap = pg.ColorMap(pos, color)
        lut = cmap.getLookupTable(0.0, 1.0, 256)

        self.img.setLookupTable(lut)
        self.img.setLevels([20*np.log10(1), 20*np.log10(600)])

        # waveform and spectrum x points
        self.scale_plots()

    def keyPressed(self, evt):
        """
        Handles key pressed while the graphs are in focus. Sends the pressed
        command to the Arduino, and re-scales the axis if sampling frequency
        is changed.
        """
        msg = int(chr(evt.key()))
        if msg in {0, 8, 9}:
            if msg == 0:
                self.sample_freq = 4000
                self.board.sample_freq = 4000
            elif msg == 8:
                self.sample_freq = 6000
                self.board.sample_freq = 6000
            elif msg == 9:
                self.sample_freq = 8000
                self.board.sample_freq = 8000

            self.scale_plots()

        self.board.send_command(msg)

    def scale_plots(self):
        """Scales the figures based on the current sampling frequency"""
        self.x = np.linspace(0, self.sample_no/self.sample_freq, self.sample_no)
        self.f = np.fft.rfftfreq(self.sample_no, 1/self.sample_freq)
        self.waveform.setXRange(0, self.x.max(), padding=0.005)
        self.spectrum.setXRange(0, self.f.max(), padding=0.005)
        self.specgram.setXRange(0, self.f.max(), padding=0.005)
        yscale = self.sample_freq/(self.img_array.shape[1]*self.yscale)
        xscale = self.sample_freq/(self.sample_no*self.xscale)
        self.img.scale(xscale, yscale)
        self.xscale *= xscale
        self.yscale *= yscale


    def align_music(self, freq):
        """Scales the self.NOTES such that the given frequency is in range"""
        while freq < self.NOTES.min() or freq > self.NOTES.max():
            while freq > self.NOTES.max():
                self.NOTES *= 2
            while freq < self.NOTES.min():
                self.NOTES /= 2
        self.note_dict = dict([(freq, note) for freq, note in zip(self.NOTES, self.note_keys)])
        return

    def set_plotdata(self, name, data_x, data_y):
        """Sets the data for the given plot name"""
        if name in self.traces:
            self.traces[name].setData(data_x, data_y)
        else:
            if name == 'waveform':
                self.traces[name] = self.waveform.plot(pen='c', width=3)
                self.waveform.setYRange(-100, 100, padding=0)
            if name == 'spectrum':
                self.traces[name] = self.spectrum.plot(pen='m', width=3)
                self.spectrum.setYRange(0, 1000, padding=0)

    def tune(self, sp_data):
        """
        Finds the closest frequency to a natural octave note from the input signal
        """
        freq_peak = self.f[np.argmax(sp_data[10:])]
        self.align_music(freq_peak)
        tuning_freq = min(self.NOTES, key=lambda x: abs(x-freq_peak))
        index_freq = np.argwhere(self.NOTES == tuning_freq)[0]
        bands = np.zeros(5)
        bands[2] = tuning_freq
        if index_freq == 0:
            bands[0] = (tuning_freq + self.NOTES[-1]/2)/2
        else:
            bands[0] = (tuning_freq + self.NOTES[index_freq-1])/2

        if index_freq == len(self.NOTES)-1:
            bands[4] = (tuning_freq + self.NOTES[0]*2)/2
        else:
            bands[4] = (tuning_freq + self.NOTES[index_freq+1]*2)/2

        bands[1] = (bands[0] + bands[2])/2
        bands[3] = (bands[4] + bands[2])/2
        bands -= freq_peak
        LED = np.argmin(np.abs(bands))
        # print(tuning_freq)
        self.board.send_command(int(LED+3))
        return

    def update(self):
        """Gathers new data and updates all the plots"""
        wf_data = self.board.get_data()
        wf_data2 =wf_data - int(np.mean(wf_data))
        self.set_plotdata(name='waveform', data_x=self.x, data_y=wf_data,)

        sp_data = np.abs(np.fft.rfft(wf_data))
        # self.tune(sp_data)

        self.set_plotdata(name='spectrum', data_x=self.f, data_y=sp_data)

        self.spectrogram_update(sp_data)

    def spectrogram_update(self, sp_data):
        """Updates the spectrogram plot"""
        # convert to dB
        psd = 20 * np.log10(sp_data + np.ones(len(sp_data))*0.001)

        # roll down one and replace leading edge with new data
        self.img_array = np.roll(self.img_array, 1, 0)
        self.img_array[0] = psd

        self.img.setImage(np.transpose(self.img_array), autoLevels=False)

    def animation(self):
        timer = QtCore.QTimer()
        timer.timeout.connect(self.update)
        timer.start(20)
        self.start()

    def start(self):
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()


class KeyPressWindow(pg.GraphicsWindow):
    """
    Inherited Class to deal with key press interrupts in the plot window.

    Parameters
    ----------
    *args : pg.GraphicsWindow() *args
    **kwargs : pg.GraphicsWindow() **kwarg.

    Attributes
    ----------
    sigKeyPress :
        Event Trigger for Key Presses.

    """
    sigKeyPress = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyPressEvent(self, ev):
        self.scene().keyPressEvent(ev)
        self.sigKeyPress.emit(ev)


if __name__ == "__main__":
    # log.basicConfig(level=log.DEBUG)
    audio_app = SpectrumAnalyser()
    audio_app.animation()
