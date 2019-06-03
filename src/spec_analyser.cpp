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


    cmd = Serial.read();

    //go through non-numeric commands
    if(cmd=='a' or cmd == 'b' or cmd=='c')
    {
        if (cmd =='a') frame_len = 256;
        else if (cmd =='b') frame_len = 512;
        else if (cmd =='c') frame_len = 800;
        else if (cmd =='d') frame_len = 1024;
        Serial.print("Recieved: ");
        Serial.println(static_cast<char>(cmd));
    }
    else cmd -= '0';

    // go through numeric commands
    if (cmd == 0) sample_freq = SAMPLE_FREQ1;
    else if(cmd < 3) mode = static_cast<state>(cmd);
    else if(cmd < 8)
    {   // two of the LEDs are mounted the wrong way round, so swap them so they
        // can light in numerical order
        if(cmd == 6)      cmd=7;
        else if(cmd == 7) cmd =6;

        digitalWrite(cmd, HIGH);
        for(int i=3; i<8; i++)
        {
            if(i != cmd)  digitalWrite(i, LOW);
        }
    }
    else if(cmd == 8) sample_freq = SAMPLE_FREQ2;
    else if(cmd == 9) sample_freq = SAMPLE_FREQ3;

    if (cmd <= 9)
    {
        // swap back
        if(cmd == 6)      cmd=7;
        else if(cmd == 7) cmd =6;

        Serial.print("Recieved: ");
        Serial.println(cmd);
    }
    else Serial.println("Command Not Found");
};

void Analyser::collect_data()
{
    unsigned long microseconds;
    unsigned int sampling_period_us = round(1000000*(1.0/sample_freq));
    static float x_old = 0;
    static float y_old = 0;
    float x;
    float y;

    for(int i=0; i<frame_len; i++)
    {
        microseconds = micros();    //Overflows after around 70 minutes!
        //Apply DC block to data
        x = (float)(analogRead(0));
        y = x - x_old + 0.995* y_old;
        x_old = x;
        y_old = y;

        //clip signal to stop overflow
        if (y > 127.0) y = 127.0;
        if (y < -127.0) y = -127.0;

        data[i] = (char)(y);
        while(micros() < (microseconds + sampling_period_us)){}
    }
    // store final element for first element of new frame
}

void Analyser::send_data()
{
    if(mode == state::AUDIO)
    {
        Serial.write(data, frame_len);
    }
}
