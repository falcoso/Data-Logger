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
    board = serial.Serial("/dev/ttyACM0", 115200, timeout=10)

    sample_no, sample_freq = setup(board)
    send_command("Audio", board)
    data = get_data(board, sample_no)
    log.debug(len(data))
    data = data - np.mean(data)
    data = np.abs(np.fft.rfft(data))
    freq_bins = np.fft.rfftfreq(len(data)*2 -1, 1/sample_freq)
    fig, ax = plt.subplots()
    line, = ax.plot(freq_bins, data)
    plt.show(block=False)

    while True:
        data = get_data(board, sample_no)
        data = data - np.mean(data)
        data = np.abs(np.fft.rfft(data))
        line.set_ydata(data)
        fig.canvas.draw()
        fig.canvas.flush_events()
