#include <Arduino.h>
#include "spec_analyser.h"

Analyser arduino;
char x = 5;
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
