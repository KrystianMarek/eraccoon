 #include "CytronMotorDriver.h"

// Define Joystick pins
const int PIN_J_FORWARD = 22;
const int PIN_J_BACK = 25;
const int PIN_J_LEFT = 24;
const int PIN_J_RIGHT = 23;

const int MAX_SPEED = 128;
const int MIN_SPEED = 50;


void setup_motors() {
  // Define the motor driver pins
  CytronMD motor_fl(PWM_PWM, 2, 3);   
  CytronMD motor_rl(PWM_PWM, 4, 5);
  CytronMD motor_fr(PWM_PWM, 6, 7);   
  CytronMD motor_rr(PWM_PWM, 8, 9);
}

void setup_joystick() {
  for(int i=22;i<26;i++)
    pinMode(i,INPUT);
}

// The setup routine runs once when you press reset.
void setup() {
  setup_motors();
  setup_joystick();
}

void j_ride(int j_forward, int j_backward, int j_left, int j_right) {
  //stop
  if (j_forward == LOW && j_backward == LOW && j_left == LOW && j_right == LOW) {
    motor_fl.setSpeed(0);
    motor_fr.setSpeed(0);
    motor_rl.setSpeed(0);
    motor_rr.setSpeed(0);
  }
  //forward
  if (j_forward == HIGH && j_backward == LOW && j_left == LOW && j_right == LOW) {
    motor_fl.setSpeed(MIN_SPEED);
    motor_fr.setSpeed(MIN_SPEED);
    motor_rl.setSpeed(MIN_SPEED);
    motor_rr.setSpeed(MIN_SPEED);
  }
  //back
  if (j_forward == LOW && j_backward == HIGH && j_left == LOW && j_right == LOW) {
    motor_fl.setSpeed(-MIN_SPEED);
    motor_fr.setSpeed(-MIN_SPEED);
    motor_rl.setSpeed(-MIN_SPEED);
    motor_rr.setSpeed(-MIN_SPEED);
  }
  //dead left 
  if (j_forward == LOW && j_backward == LOW && j_left == HIGH && j_right == LOW) {
    motor_fl.setSpeed(-MIN_SPEED);
    motor_fr.setSpeed(MIN_SPEED);
    motor_rl.setSpeed(-MIN_SPEED);
    motor_rr.setSpeed(MIN_SPEED);
  }
  //dead right
  if (j_forward == LOW && j_backward == LOW && j_left == LOW && j_right == HIGH) {
    motor_fl.setSpeed(MIN_SPEED);
    motor_fr.setSpeed(-MIN_SPEED);
    motor_rl.setSpeed(MIN_SPEED);
    motor_rr.setSpeed(-MIN_SPEED);
  }
}

// The loop routine runs over and over again forever.
void loop() {
  j_ride(digitalRead(PIN_J_FORWARD), digitalRead(PIN_J_BACK), digitalRead(PIN_J_LEFT), digitalRead(PIN_J_RIGHT));
}