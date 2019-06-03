import scipy.signal as sp
import numpy as np


class DataLogger:
    def __init__(self, frame_len, sample_freq):
        self.frame_len = frame_len
        self.sample_freq = sample_freq
        self.spec_size = 100

        self.specgram = np.zeros((self.spec_size, int(self.frame_len/2+1)))

        self.freq_lo = 100
        self.freq_hi = 2500

        # setup digital filters
        self.set_filters()

        return

    def get_specgram(self):
        return self.specgram

    def set_filters(self):
        fn_lo = self.freq_lo/self.sample_freq
        fn_hi = self.freq_hi/self.sample_freq

        self.blo, self.alo = sp.butter(2, fn_lo*2, btype='highpass')
        try:
            self.b, self.a = sp.butter(2, fn_hi*2)
        except ValueError:
            pass

    def get_data_axis(self):
        freq_bins = np.fft.rfftfreq(self.frame_len, 1/self.sample_freq)
        time_bins = np.linspace(0, self.frame_len/self.sample_freq, self.frame_len)
        return freq_bins, time_bins

    def set_sample_freq(self, freq):
        self.sample_freq = freq
        self.set_filters()
        self.specgram = np.zeros((self.spec_size, int(self.frame_len/2+1)))
        return self.get_data_axis()

    def set_frame_len(self, frame_len):
        self.frame_len = frame_len
        self.specgram = np.zeros((self.spec_size, int(self.frame_len/2+1)))
        return self.get_data_axis()

    def set_low_cutoff(self, freq):
        self.freq_lo = freq
        self.set_filters()
        return

    def set_high_cutoff(self, freq):
        self.freq_hi = freq
        self.set_filters()
        return

    def process(self, wf_data):
        # high pass filter
        wf_data = sp.filtfilt(self.blo, self.alo, wf_data)

        # if sampling frequency allows, low pass filter to reduce quantisation
        if self.freq_hi < self.sample_freq/2:
            wf_data = sp.filtfilt(self.b, self.a, wf_data)

        sp_data = np.abs(np.fft.rfft(wf_data))

        # get power spectral density for spectrogram
        psd = 20 * np.log10(sp_data + np.ones(len(sp_data))*0.1)
        self.specgram = np.roll(self.specgram, 1, 0)
        self.specgram[0] = psd

        return sp_data, wf_data
