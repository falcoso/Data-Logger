#include <Arduino.h>
#include "spec_analyser.h"

Analyser arduino;

void setup()
{
    arduino = Analyser();
    arduino.setup();
};

void loop()
{
    // Serial.println("Entering Loop");
    arduino.read_terminal();
    arduino.collect_data();
    arduino.send_data();
    // arduino.mode = state::SETUP;
};
