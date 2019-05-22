import serial
import matplotlib.pyplot as plt
import numpy as np
import logging as log
import struct

def send_command(message, board):
    message_dict = {"Setup": '0',
                    "FFT": '1',
                    "Audio":'2'}

    if message not in message_dict.keys():
        raise ValueError("Message not configured on Arduino")

    # send message
    board.write(message_dict[message].encode())
    log.debug("[+] Message Sent: {} ({})".format(message_dict[message], message))
    #check confirmation:
    line = board.readline()
    log.debug("[+] Confirmation recieved: {}".format(line))
    line = str(line, "utf-8")
    if message_dict[message] not in line:
        raise RuntimeError("Unable to acknowledge message:{}".format(line))
    return

def process_data(raw_data):
    rec = np.array([raw_data[i*4:i*4+4] for i in range(len(raw_data)//4)])
    formatted = np.array([struct.unpack('f', i)[0] for i in rec])
    return formatted


def setup(board):
    line = str(board.readline(), "utf-8")
    print(line)
    if "Setup Complete" not in line:
        raise RuntimeError("Unable to complete setup")

    samples = str(board.readline(), "utf-8").split(":")
    samples = int(samples[-1])
    log.debug("[+] Sample rate: {}".format(samples))
    return samples

def get_data(board):
    data = board.read(128*2)
    data = np.array(struct.unpack('h'*128, data))
    return data

if __name__ == "__main__":
    log.basicConfig(level=log.DEBUG)
    board = serial.Serial("/dev/ttyACM0", 115200, timeout=10)

    # sample_no = setup(board)
    send_command("Audio", board)
    data = get_data(board)
    data = data - np.mean(data)
    data = np.abs(np.fft.rfft(data))
    fig, ax = plt.subplots()
    line, = ax.plot(data)
    # plt.ylim(0,1000)
    plt.show(block=False)

    while True:
        data = get_data(board)
        data = data - np.mean(data)
        data = np.abs(np.fft.rfft(data))
        line.set_ydata(data)
        fig.canvas.draw()
        fig.canvas.flush_events()
