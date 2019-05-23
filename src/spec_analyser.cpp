#include "spec_analyser.h"

Analyser::Analyser()
{
    mode = state::SETUP;
    frame_len = FRAME_LEN;
    sample_freq = SAMPLE_FREQ;
};

void Analyser::setup()
{
    Serial.begin(BAUD);
    Serial.println("Setup Complete");
    Serial.print("Sample no: ");
    Serial.println(frame_len);
    Serial.print("Sample freq: ");
    Serial.println(sample_freq);
};

void Analyser::read_terminal()
{
    int cmd;
    if(!Serial.available()) return;

    cmd = Serial.read() - '0';
    if(cmd <4)
    {
        mode = static_cast<state>(cmd);
        Serial.print("Recieved: ");
        Serial.println(static_cast<int>(mode));
    }
    else
    {
        Serial.println("Command not recognised");
    };
};

void Analyser::collect_data()
{
    unsigned long microseconds;
    unsigned int sampling_period_us = round(1000000*(1.0/SAMPLE_FREQ));

    for(int i=0; i<FRAME_LEN; i++)
    {
        microseconds = micros();    //Overflows after around 70 minutes!

        datar[i] = analogRead(0);
        datai[i] = 0;

        while(micros() < (microseconds + sampling_period_us)){
        }
    }
}

void Analyser::send_data()
{
    if(mode == state::AUDIO)
    {
        Serial.write((char*)(datar), sizeof(datar));
    }
}

void Analyser::fft_data()
{

}
