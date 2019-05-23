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
    arduino.read_terminal();
    arduino.collect_data();
    arduino.send_data();
};
