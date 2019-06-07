import scipy.signal as sp
import numpy as np
import glob
from skimage.measure import compare_ssim


class DataLogger:
    def __init__(self, frame_len, sample_freq):
        self.frame_len = frame_len
        self.sample_freq = sample_freq
        self.spec_size = 100

        self.specgram = np.zeros((self.spec_size, int(self.frame_len/2+1)))

        self.freq_lo = 150
        self.freq_hi = 2500

        # middle octave for tuning
        self.NOTES = np.array([440, 493.88, 523.25, 587.33, 659.25, 698.46, 783.99, 880])

        # counter to keep track of recording
        self.record_counter = 0

        # setup digital filters
        self.set_filters()

        return

    def get_specgram(self):
        return self.specgram

    def set_filters(self):
        fn_lo = self.freq_lo/self.sample_freq
        fn_hi = self.freq_hi/self.sample_freq

        self.blo, self.alo = sp.butter(4, fn_lo*2, btype='highpass')
        try:
            self.b, self.a = sp.butter(2, fn_hi*2)
        except ValueError:
            pass

    def get_data_axis(self):
        self.freq_bins = np.fft.rfftfreq(self.frame_len, 1/self.sample_freq)
        self.time_bins = np.linspace(0, self.frame_len/self.sample_freq, self.frame_len)
        return self.freq_bins, self.time_bins

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
        self.freq_peak = self.freq_bins[np.argmax(sp_data)]

        return sp_data, wf_data

    def tune(self):
        """
        Finds the closest frequency to a natural octave note from the input signal
        """
        if self.freq_peak < self.freq_lo:
            return
        tuning_freq = self.get_tuning_freq(self.freq_peak)

        # create 5 bins around the closest frequency to the current peak
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

        # find the LED to return by looking at the closest
        bands -= self.freq_peak
        LED = np.argmin(np.abs(bands))
        return self.freq_peak, tuning_freq, LED

    def get_tuning_freq(self, freq):
        """Returns the not the current maxe frequency is closest to"""
        if freq < self.freq_lo:
            return

        while freq < self.NOTES.min() or freq > self.NOTES.max():
            while freq > self.NOTES.max():
                self.NOTES *= 2
            while freq < self.NOTES.min():
                self.NOTES /= 2
        tuning_freq = min(self.NOTES, key=lambda x: abs(x-freq))
        return tuning_freq

    def record(self, file_name):
        self.record_counter += 1
        if self.record_counter > self.spec_size:
            fullname = "{}_{}_{}_{}.npy".format(file_name, self.sample_freq,
                                                self.frame_len, self.spec_size)
            np.save("./record_files/"+fullname, self.specgram)
            print("Record saved as {}".format(fullname))
            self.record_counter = 0
            return True
        else:
            return False

    def audio_match(self, cmp_file=None, new_file=None):
        self.record_counter += 1
        if self.record_counter > self.spec_size:
            if cmp_file is None:
                footer = "_{}_{}_{}.npy".format(self.sample_freq, self.frame_len,
                                                self.spec_size)

                files = glob.glob("./record_files/*{}".format(footer))
                match = ''
                mssim_best = -10
                for file in files:
                    record = np.load(file)
                    mssim = compare_ssim(record, self.specgram, win_size=51)
                    if mssim > mssim_best:
                        match = file
                        mssim_best = mssim
                    print("MSSIM of compared to {}: {}".format(file, mssim))

                file_name = match
                match = match.replace(footer, '')
                match = match.replace("./record_files/", '')
                print("Best estimate: {}".format(match))
                match_split = match.split('_')
                if match_split[-1].isdigit():
                    match = match.replace(match_split[-1], '')

                files = glob.glob("./record_files/{}*".format(match))
                match += str(len(files)+1) + footer
                np.save("./record_files/"+match, self.specgram)
                print("Record saved as {}".format(match))

            else:
                record_fullname = "{}_{}_{}_{}.npy".format(cmp_file, self.sample_freq,
                                                           self.frame_len, self.spec_size)
                record = np.load("./record_files/"+record_fullname)

                mssim = compare_ssim(record, self.specgram, win_size=51)
                print("MSSIM of new recording: {}".format(mssim))

                if new_file is not None:
                    record_fullname = "{}_{}_{}.npy".format(new_file, self.sample_freq,
                                                            self.frame_len, self.spec_size)
                    np.save("./record_files"+record_fullname, self.specgram)
                    print("Comparison saved as {}".format(record_fullname))

            self.record_counter = 0
            return True
        else:
            return False
