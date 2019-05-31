import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import sys
import serial
import logging as log
import struct


class ArduinoBoard:
    def __init__(self, port, baud, timeout):
        self.board = serial.Serial(port, baud, timeout=timeout)
        self.sample_no, self.sample_freq = self.setup()
        self.LED = None
        return

    def setup(self):
        line = str(self.board.readline(), "utf-8")
        if "Setup Complete" not in line:
            raise RuntimeError("Unable to complete setup, recieved: {}".format(line))

        frame_len = str(self.board.readline(), "utf-8").split(":")
        frame_len = int(frame_len[-1])
        log.debug("[+] Sample rate: {}".format(frame_len))
        sample_freq = str(self.board.readline(), "utf-8").split(":")
        sample_freq = int(sample_freq[-1])
        log.debug("[+] Sample freq: {}".format(sample_freq))
        return frame_len, sample_freq

    def send_command(self, message):
        message_dict = {"Setup": '0',
                        "FFT": '1',
                        "Audio": '2'}

        if message not in message_dict.keys():
            raise ValueError("Message not configured on Arduino")

        # send message
        self.board.write(message_dict[message].encode("utf-8"))
        line = self.board.readline()
        log.debug("[+] Message Sent: {} ({})".format(message_dict[message], message))
        # check confirmation:
        log.debug("[+] Confirmation recieved: {}".format(line))
        line = str(line, "utf-8")
        if message_dict[message] not in line:
            raise RuntimeError("Unable to acknowledge message:{}".format(line))
        return

    def change_LED(self, led):
        if isinstance(led, int):
            led = str(led)
        ledencode = {'1': '4', '2': '5', '3': '6', '4': '8', '5': '7'}
        try:
            if led != self.LED:
                self.board.write(ledencode[led].encode("utf-8"))
                self.board.write(ledencode[self.LED].encode("utf-8"))
                self.LED = led

        except KeyError:
            pass
        return

    def get_data(self):
        data = self.board.read(self.sample_no*2)
        log.debug(len(data))
        data = np.array(struct.unpack('h'*self.sample_no, data))
        return data


class SpectrumAnalyser:
    def __init__(self):

        self.board = ArduinoBoard("/dev/ttyACM0", 115200, timeout=5)
        self.sample_no = self.board.sample_no
        self.sample_freq = self.board.sample_freq

        self.NOTES = np.array([440, 493.88, 523.25, 587.33, 659.25, 698.46, 783.99, 880])
        self.note_keys = ["A", "B", "C", "D", "E", "F", "G", "A+"]
        self.note_dict = dict([(freq, note) for freq, note in zip(self.NOTES, self.note_keys)])
        # tell Arduino to start sending data
        self.board.send_command("Audio")

        # pyqtgraph stuff
        pg.setConfigOptions(antialias=True)
        self.traces = dict()
        self.app = QtGui.QApplication(sys.argv)
        self.win = KeyPressWindow(title='Spectrum Analyzer')
        self.win.setWindowTitle('Spectrum Analyzer')

        self.win.sigKeyPress.connect(lambda x: self.win.keyPressed(self.board, x))

        self.waveform = self.win.addPlot(
            title='WAVEFORM', row=1, col=1, labels={'bottom': "Time (s)"})
        self.spectrum = self.win.addPlot(
            title='SPECTRUM', row=1, col=2, labels={'bottom': "Frequency (Hz)"})
        self.specgram = self.win.addPlot(
            title='SPECTROGRAM', row=2, col=1, colspan=2,
            labels={'bottom': "Frequency (Hz)"})

        # waveform and spectrum x points
        self.x = np.linspace(0, self.sample_no/self.sample_freq, self.sample_no)
        self.f = np.fft.rfftfreq(self.sample_no, 1/self.sample_freq)

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
        # self.img.setLevels([20*np.log10(0.01), 20*np.log10(20000)])

        yscale = 1.0/(self.img_array.shape[1]/self.f[-1])
        self.img.scale(self.sample_freq/self.sample_no, yscale)

    def start(self):
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()

    def align_music(self, freq):
        while freq < self.NOTES.min() or freq > self.NOTES.max():
            while freq > self.NOTES.max():
                self.NOTES *= 2
            while freq < self.NOTES.min():
                self.NOTES /= 2
        self.note_dict = dict([(freq, note) for freq, note in zip(self.NOTES, self.note_keys)])
        return

    def set_plotdata(self, name, data_x, data_y):
        if name in self.traces:
            self.traces[name].setData(data_x, data_y)
        else:
            if name == 'waveform':
                self.traces[name] = self.waveform.plot(pen='c', width=3)
                self.waveform.setYRange(0, 1000, padding=0)
                self.waveform.setXRange(0, self.x.max(), padding=0.005)
            if name == 'spectrum':
                self.traces[name] = self.spectrum.plot(pen='m', width=3)
                self.spectrum.setYRange(0, 2000, padding=0)
                self.spectrum.setXRange(0, self.f.max(), padding=0.005)

    def tune(self, sp_data):
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
        self.board.change_LED(LED)
        return

    def update(self):
        wf_data = self.board.get_data()
        wf_data -= int(np.mean(wf_data))
        self.set_plotdata(name='waveform', data_x=self.x, data_y=wf_data,)

        sp_data = np.abs(np.fft.rfft(wf_data))
        self.tune(sp_data)

        self.set_plotdata(name='spectrum', data_x=self.f, data_y=sp_data)

        self.spectrogram_update(sp_data)

    def spectrogram_update(self, sp_data):
        # convert to dB
        psd = 20 * np.log10(sp_data + np.ones(len(sp_data))*0.001)

        # roll down one and replace leading edge with new data
        self.img_array = np.roll(self.img_array, 1, 0)
        self.img_array[0] = psd

        self.img.setImage(np.transpose(self.img_array), autoLevels=True)

    def animation(self):
        timer = QtCore.QTimer()
        timer.timeout.connect(self.update)
        timer.start(20)
        self.start()


class KeyPressWindow(pg.GraphicsWindow):
    sigKeyPress = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyPressEvent(self, ev):
        self.scene().keyPressEvent(ev)
        self.sigKeyPress.emit(ev)

    def keyPressed(self, board, evt):
        board.change_LED(chr(evt.key()))


if __name__ == "__main__":
    # log.basicConfig(level=log.DEBUG)
    audio_app = SpectrumAnalyser()
    audio_app.animation()
