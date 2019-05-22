#ifndef spec
#define spec

#include <fix_fft.h>
#include <Arduino.h>

#define FRAME_LEN 128
#define SAMPLE_FREQ 4000

enum class state{SETUP, FFT, AUDIO};

class Analyser
{
public:
    state mode;
    int frame_len;
    int sample_freq;
    int datar[FRAME_LEN];
    int datai[FRAME_LEN];

    Analyser();
    void setup(int baud);
    void read_terminal();
    void collect_data();
    void send_data();
    void fft_data();
};

#endif
