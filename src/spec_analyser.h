#ifndef spec
#define spec

#include <Arduino.h>

#define FRAME_LEN 1024
#define SAMPLE_FREQ1 4000
#define SAMPLE_FREQ2 7000
#define SAMPLE_FREQ3 9000
#define FILTER_GAIN 1
#define BAUD 230400

enum class state{SETUP, FFT, AUDIO};

class Analyser
{
public:
    state mode;
    int frame_len;
    int sample_freq;
    char data[FRAME_LEN];

    Analyser();
    void setup();
    void read_terminal();
    void collect_data();
    void send_data();
    void fft_data();
};

#endif
