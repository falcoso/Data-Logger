import serial
import matplotlib.pyplot as plt
import numpy as np
import logging as log
import struct


def send_command(message, board):
    message_dict = {"Setup": '0',
                    "FFT": '1',
                    "Audio": '2'}

    if message not in message_dict.keys():
        raise ValueError("Message not configured on Arduino")

    # send message
    board.write(message_dict[message].encode("utf-8"))
    line = board.readline()
    log.debug("[+] Message Sent: {} ({})".format(message_dict[message], message))
    # check confirmation:
    log.debug("[+] Confirmation recieved: {}".format(line))
    line = str(line, "utf-8")
    if message_dict[message] not in line:
        raise RuntimeError("Unable to acknowledge message:{}".format(line))
    return


def setup(board):
    line = str(board.readline(), "utf-8")
    if "Setup Complete" not in line:
        raise RuntimeError("Unable to complete setup, recieved: {}".format(line))

    frame_len = str(board.readline(), "utf-8").split(":")
    frame_len = int(frame_len[-1])
    log.debug("[+] Sample rate: {}".format(frame_len))
    sample_freq = str(board.readline(), "utf-8").split(":")
    sample_freq = int(sample_freq[-1])
    log.debug("[+] Sample rate: {}".format(sample_freq))
    return frame_len, sample_freq


def get_data(board, frame_len):
    data = board.read(frame_len*2)
    log.debug(len(data))
    data = np.array(struct.unpack('h'*frame_len, data))
    return data


if __name__ == "__main__":
    # log.basicConfig(level=log.DEBUG)

    try:
        board = serial.Serial("/dev/ttyACM0", 115200, timeout=5)

        sample_no, sample_freq = setup(board)
        # tell Arduino to start sending data
        send_command("Audio", board)

        # get initial set of data
        data_time = get_data(board, sample_no)
        data_time = data_time - np.mean(data_time)
        freq_bins = np.fft.rfftfreq(len(data_time), 1/sample_freq)
        time_stamp = np.linspace(0, len(data_time)/sample_freq, len(data_time))
        print(time_stamp)
        data_freq = np.abs(np.fft.rfft(data_time))
        fig, (ax1, ax2, ax3) = plt.subplots(3)
        line1, = ax1.plot(freq_bins, data_freq)
        line2, = ax2.plot(time_stamp, data_time)
        ax1.set_ylim(bottom=0)
        ax1.set_xlim(0, sample_freq/2)
        plt.show(block=False)

        # get note trace
        index = 0
        trace_size = 100
        freq_trace = np.zeros(trace_size)
        trace_time = np.linspace(0, len(data_time)*trace_size/sample_freq, trace_size)
        freq_trace[index] = freq_bins[np.argmax(data_freq)]
        index +=1
        line3, = ax3.plot(freq_trace, trace_time)
        ax3.set_xlim(0, sample_freq/2)
        ax3.set_ylim(0, trace_time.max())

        while True:
            data_time = get_data(board, sample_no)
            data_time = data_time - np.mean(data_time)
            data_freq = np.abs(np.fft.rfft(data_time))
            freq_trace[index] = freq_bins[np.argmax(data_freq)]
            index = (index +1) % trace_size
            # reset the height if it changes too much
            if data_freq.max() > ax1.get_ylim()[1] or data_freq.max() < ax1.get_ylim()[1]/2:
                ax1.set_ylim(0, data_freq.max()*1.1)
            if data_time.max() > ax2.get_ylim()[1] or data_time.max() < ax2.get_ylim()[1]/2:
                ax2.set_ylim(-data_time.max()*1.1, data_time.max()*1.1)


            line1.set_ydata(data_freq)
            line2.set_ydata(data_time)
            line3.set_xdata(freq_trace)
            fig.canvas.draw()
            fig.canvas.flush_events()

    except Exception as e:
        # board.flush()
        board.close()
        raise e
