/**************************************************************
* MUX_control
* Vincent Musso, Duttlab
* March 25, 2019
* 
* This sketch provides the mechanisms for using the
* SparkFun Multiplexer Breakout - 8 Channel (74HC4051)
* to allow the user to select which of 3 digital input
* devices to designate as the desired input via user
* input from the serial monitor.
*
* Hardware Hookup:
* Mux Breakout ----------- Arduino
*      S0 ------------------- 2
*      S1 ------------------- 3
*      S2 ------------------- 4
*      Z -------------------- 5
*     VCC ------------------- 5V
*     GND ------------------- GND
*     (VEE should automatically be
*      connected to GND via the 
*      closed jumper JP1)
*      
* The multiplexer's independent I/O (Y0-Y2) can each be wired
* up to a differnt digial signal producing device.
* 
* Code can be easily modified for use of more than 3 I/O pins
* or if Z is to be used as an output instead.
**************************************************************/
const int selectPins[3] = {2, 3, 4};
const int zInput = 5;                     // Any pin 2-13 for digital I/O. Pins A0-A5 for analog I/O

void setup() {
  Serial.begin(9600);
  // while(!Serial) {;}                      // wait for serial port to connect (possibly don't need, works fine w/o it)
  for(int i = 0; i < 3; i++) {             
    pinMode(selectPins[i], OUTPUT);
    digitalWrite(selectPins[i], LOW);          // initialize all selects to 0, making Y0 initial input
  }
  //pinMode(zInput, INPUT);                      // Change to OUTPUT if outputting signal from Arduino board
  //delay(250);
  //analogWrite(zInput, 255);
  Serial.println("Initialized...Enter 1 for Confocal, 2 for ODMR, or 3 for Pulsed."); // changed from CW-ESR to ODMR, by Gurudev August 11, 2025
}

// modified by Gurudev on Dec. 12, 2019 -- will use newline to terminate input
void loop() {
  if (Serial.available() > 0) {
    String user_input = Serial.readStringUntil('\n'); 
    change_mux_output(user_input);                         
  }
}


// modified by Gurudev on Dec. 12, 2019
void change_mux_output(String input){
    int selector = check_input(input);
    if (selector >= 0){
      Serial.println("Input is in range");
      for(int i = 0; i < 2; i++) {                              // Use binary representation of integer input to assign
        digitalWrite(selectPins[i], (selector & 1));       // the I/O channel. Only 2 of the 3 select pins change,
        selector >>= 1;                                    // so loop until i = 2 for first 2 bits. Increase upper bound on i for use with more I/O pins.
      }                                                         //   Input |  S2   |  S1   |  S0   |  I/O selected
    } else {                                                    //   ---------------------------------------------
        Serial.println("Input out of range");                   //     0   |   0   |   0   |   0   |     Y0
    }                                                           //     1   |   0   |   0   |   1   |     Y1
                                                                //     2   |   0   |   1   |   0   |     Y2                         
}

// modified by Gurudev on Dec. 12, 2019
int check_input(String input){
  if (input.equals("1")){return 0;}
  else if (input.equals("2")){return 1;}
  else if (input.equals("3")){return 2;}
  else return -1;
} 