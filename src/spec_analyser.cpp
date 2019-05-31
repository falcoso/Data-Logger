#include "spec_analyser.h"

Analyser::Analyser()
{
    mode = state::SETUP;
    frame_len = FRAME_LEN;
    sample_freq = SAMPLE_FREQ1;
    pinMode(3, OUTPUT);
    pinMode(4, OUTPUT);
    pinMode(5, OUTPUT);
    pinMode(6, OUTPUT);
    pinMode(7, OUTPUT);
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
    if (cmd == 0) sample_freq = SAMPLE_FREQ1;
    else if(cmd < 3) mode = static_cast<state>(cmd);
    else if(cmd < 8) digitalWrite(cmd, !digitalRead(cmd));
    else if(cmd == 8) sample_freq = SAMPLE_FREQ2;
    else if(cmd == 9) sample_freq = SAMPLE_FREQ3;

    if (cmd <= 9)
    {
        Serial.print("Recieved: ");
        Serial.println(cmd);
    }
    else Serial.println("Command Not Found");
};

void Analyser::collect_data()
{
    unsigned long microseconds;
    unsigned int sampling_period_us = round(1000000*(1.0/sample_freq));

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
