#ifndef spec
#define spec

#include <Arduino.h>

#define FRAME_LEN 400
#define SAMPLE_FREQ1 4000
#define SAMPLE_FREQ2 6000
#define SAMPLE_FREQ3 8000
#define FILTER_GAIN 1
#define ALPHA = 0.3
#define BAUD 115200

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
