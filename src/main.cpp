#include <Arduino.h>
#include "spec_analyser.h"

#define BAUD 74880

Analyser arduino;

void setup()
{
    arduino = Analyser();
    arduino.setup(BAUD);
};

void loop()
{
    arduino.read_terminal();
    arduino.collect_data();
    arduino.send_data();
    // arduino.mode = state::SETUP;
};
