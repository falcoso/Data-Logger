import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import scipy.signal as sp
import sys
import logging as log
import struct
import imagehash
from PIL import Image
from arduino import ArduinoBoard

class SpectrumGUI:
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
        self.board = ArduinoBoard("/dev/ttyACM0", 230400, timeout=5)
        self.sample_no = self.board.sample_no
        self.sample_freq = self.board.sample_freq
        self.fc = 2500
        self.fcl = 100
        fn = self.fc/self.sample_freq
        fnlo = self.fcl/self.sample_freq
        self.blo, self.alo = sp.butter(2, fnlo*2, btype='highpass')
        try:
            self.b, self.a = sp.butter(2, fn*2)
        except ValueError:
            pass

        self.record_counter =0
        self.lock_hash = None

        self.mode = None
        self.xscale = 1
        self.yscale = 1
        self.lock_sequence = []

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
        msg = chr(evt.key())
        if msg == ' ':
            cmd = input('>>\n')
            self.txt_command(cmd)
            return
        else:
            msg = int(msg)
        if msg in {0, 8, 9}:
            if msg == 0:
                self.sample_freq = 4000
                self.board.sample_freq = 4000
            elif msg == 8:
                self.sample_freq = 7000
                self.board.sample_freq = 7000
            elif msg == 9:
                self.sample_freq = 9000
                self.board.sample_freq = 9000

            fn = self.fc/self.sample_freq
            fnlo = self.fcl/self.sample_freq
            self.blo, self.alo = sp.butter(2, fnlo*2, btype='highpass')
            try:
                self.b, self.a = sp.butter(2, fn*2)
            except ValueError:
                pass
            self.scale_plots()
            self.board.send_command(msg)

    def txt_command(self, cmd):
        """Converts a text based input into a command to send to the board."""
        cmd = cmd.split(' ')
        if cmd[0] == 'h':
            print("Text based interface:")
            print("filt   <frequency kHz> - sets the low pass digital filter frequency < 4.5kHz")
            print("sample <frequency kHz> - sets the sampling frequency of 4kHz, 7kHz, or 9kHz")
            print("frame  <frame length>  - number of samples per frame {256, 512, 800, 1024}")

        elif cmd[0] == 'mode':
            self.mode = cmd[1]
            return

        elif cmd[0] == 'filter':
            try:
                new_fc = int(cmd[1])
                if new_fc > 4500:
                    raise ValueError('')
                self.fc = int(cmd[1])
                fn = self.fc/self.sample_freq
                fnlo = self.fcl/self.sample_freq
                self.blo, self.alo = sp.butter(2, fnlo*2, btype='highpass')
                self.b, self.a = sp.butter(2, fn*2)
            except ValueError:
                print("Filter Frequency must be < 4.5k")
                return

        elif cmd[0] == 'sample':
            try:
                cmd = int(cmd[1])
                if cmd not in {4, 7, 9}:
                    raise ValueError()
                else:
                    self.sample_freq = cmd*1000
                    self.board.sample_freq = cmd*1000

            except ValueError:
                print("Sample rate must be 4, 7, or 9 kHz")
                return

            fn = self.fc/self.sample_freq
            fnlo = self.fcl/self.sample_freq
            self.blo, self.alo = sp.butter(2, fnlo*2, btype='highpass')
            try:
                self.b, self.a = sp.butter(2, fn*2)
            except ValueError:
                pass

            self.board.send_command("Sample {}k".format(int(cmd)))
            self.scale_plots()

        elif cmd[0] == 'frame':
            try:
                cmd = int(cmd[1])
                if cmd not in {256, 512, 800, 1024}:
                    raise ValueError()
                else:
                    self.sample_no = cmd
                    self.board.sample_no = cmd
                self.img_array = np.zeros((100, int(self.sample_no/2+1)))
                self.board.send_command("Frame {}".format(cmd))
                self.scale_plots()
            except ValueError:
                print("Frame length must be 256, 512, 800, 1024")
                return

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

    def set_plotdata(self, name, data_x, data_y):
        """Sets the data for the given plot name"""
        if name in self.traces:
            self.traces[name].setData(data_x, data_y)
        else:
            if name == 'waveform':
                self.traces[name] = self.waveform.plot(pen='c', width=3)
                self.waveform.setYRange(-50, 50, padding=0)
            if name == 'spectrum':
                self.traces[name] = self.spectrum.plot(pen='m', width=3)
                self.spectrum.setYRange(0, 1000, padding=0)

    def tune(self, freq_peak):
        """
        Finds the closest frequency to a natural octave note from the input signal
        """
        if freq_peak < self.fcl:
            return
        tuning_freq = self.get_tuning_freq(freq_peak)
        # print(np.argwhere(self.NOTES == tuning_freq))
        # print(self.NOTES)
        # print(freq_peak)
        index_freq = np.argwhere(self.NOTES == tuning_freq)[0][0]
        bands = np.zeros(5)
        bands[2] = tuning_freq
        if index_freq == 0:
            bands[0] = (tuning_freq + self.NOTES[-1]/2)/2
        else:
            bands[0] = (tuning_freq + self.NOTES[index_freq-1])/2

        if index_freq == len(self.NOTES)-1:
            bands[4] = (tuning_freq + self.NOTES[0]*2)/2
        else:
            bands[4] = (tuning_freq + self.NOTES[index_freq+1])/2

        bands[1] = (bands[0] + bands[2])/2
        bands[3] = (bands[4] + bands[2])/2
        # print(self.NOTES)
        # print(bands)
        bands -= freq_peak
        LED = np.argmin(np.abs(bands))
        if LED != self.board.LED:
            self.board.LED = LED
            print("[+] Actual peak: {}".format(freq_peak))
            print("[+] Closest Note: {}".format(tuning_freq))
            self.board.send_command(int(LED+3))
        return

    def get_tuning_freq(self, freq):
        """Returns the not the current maxe frequency is closest to"""
        if freq < 50:
            return

        while freq < self.NOTES.min() or freq > self.NOTES.max():
            while freq > self.NOTES.max():
                self.NOTES *= 2
            while freq < self.NOTES.min():
                self.NOTES /= 2
        tuning_freq = min(self.NOTES, key=lambda x: abs(x-freq))
        return tuning_freq

    def record(self, freq):
        self.record_counter += 1
        if self.record_counter > 100:
            if self.lock_hash is None:
                print("Initial hash:")
                self.lock_hash = imagehash.dhash(Image.fromarray(self.img_array), hash_size = 16)
                np.save("outfile6.npy", self.img_array)
            else:
                print("Comparison hash:")
                new_hash = imagehash.dhash(Image.fromarray(self.img_array),hash_size = 16)
                print(new_hash)
                print(self.lock_hash)
                print(self.lock_hash-new_hash)
                self.lock_hash = new_hash
            self.record_counter = 0
        # tuning_freq = self.get_tuning_freq(freq)
        #
        # if len(self.lock_sequence) > 10:
        #     print(self.lock_sequence)
        #     return
        #
        # try:
        #     if tuning_freq != self.lock_sequence[-1]:
        #         self.lock_sequence.append(tuning_freq)
        # except IndexError as e:
        #     if len(self.lock_sequence) == 0:
        #         self.lock_sequence.append(tuning_freq)
        #     else:
        #         raise e

    def update(self):
        """Gathers new data and updates all the plots"""
        try:
            wf_data = self.board.get_data()
        except struct.error:
            print("[+] Unpacking error")
            return

        # if the sample rate is high enough, filter to reduce quantisation error
        wf_data = sp.filtfilt(self.blo, self.alo, wf_data)
        if self.fc < self.sample_freq/2:
            wf_data = sp.filtfilt(self.b, self.a, wf_data)

        self.set_plotdata(name='waveform', data_x=self.x, data_y=wf_data,)

        sp_data = np.abs(np.fft.rfft(wf_data))

        self.set_plotdata(name='spectrum', data_x=self.f, data_y=sp_data)

        self.spectrogram_update(sp_data)
        if self.mode == 'tune':
            freq_peak = self.f[np.argmax(sp_data[10:])]
            self.tune(freq_peak)
        elif self.mode == 'record':
            freq_peak = self.f[np.argmax(sp_data[10:])]
            self.record(freq_peak)

    def spectrogram_update(self, sp_data):
        """Updates the spectrogram plot"""
        # convert to dB
        psd = 20 * np.log10(sp_data + np.ones(len(sp_data))*0.1)
        # psd = sp_data

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
    log.basicConfig(level=log.DEBUG)
    audio_app = SpectrumGUI()
    audio_app.animation()
