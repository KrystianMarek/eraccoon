 #include "CytronMotorDriver.h"

// Define Joystick pins
const int J_FORWARD = 22;
const int J_BACK = 25;
const int J_LEFT = 24;
const int J_RIGHT = 23;

const int MAX_SPEED = 128;
const int MIN_SPEED = 50;


// Define the motor driver pins
CytronMD motor_fl(PWM_PWM, 2, 3);   
CytronMD motor_rl(PWM_PWM, 4, 5);
CytronMD motor_fr(PWM_PWM, 6, 7);   
CytronMD motor_rr(PWM_PWM, 8, 9);

// The setup routine runs once when you press reset.

void init_joystick() {
  for(int i=22;i<26;i++)
    pinMode(i,INPUT);
}

void setup() {
  init_joystick();
}

void j_ride(int jForward, int jBackward, int jLeft, int jRight) {
  //stop
  if (jForward == LOW && jBackward == LOW && jLeft == LOW && jRight == LOW) {
    motor_fl.setSpeed(0);
    motor_fr.setSpeed(0);
    motor_rl.setSpeed(0);
    motor_rr.setSpeed(0);
  }
  //forward
  if (jForward == HIGH && jBackward == LOW && jLeft == LOW && jRight == LOW) {
    motor_fl.setSpeed(MIN_SPEED);
    motor_fr.setSpeed(MIN_SPEED);
    motor_rl.setSpeed(MIN_SPEED);
    motor_rr.setSpeed(MIN_SPEED);
  }
  //back
  if (jForward == LOW && jBackward == HIGH && jLeft == LOW && jRight == LOW) {
    motor_fl.setSpeed(-MIN_SPEED);
    motor_fr.setSpeed(-MIN_SPEED);
    motor_rl.setSpeed(-MIN_SPEED);
    motor_rr.setSpeed(-MIN_SPEED);
  }
  //dead left 
  if (jForward == LOW && jBackward == LOW && jLeft == HIGH && jRight == LOW) {
    motor_fl.setSpeed(-MIN_SPEED);
    motor_fr.setSpeed(MIN_SPEED);
    motor_rl.setSpeed(-MIN_SPEED);
    motor_rr.setSpeed(MIN_SPEED);
  }
  //dead right
  if (jForward == LOW && jBackward == LOW && jLeft == LOW && jRight == HIGH) {
    motor_fl.setSpeed(MIN_SPEED);
    motor_fr.setSpeed(-MIN_SPEED);
    motor_rl.setSpeed(MIN_SPEED);
    motor_rr.setSpeed(-MIN_SPEED);
  }
}



// The loop routine runs over and over again forever.
void loop() {
  j_ride(digitalRead(J_FORWARD), digitalRead(J_BACK), digitalRead(J_LEFT), digitalRead(J_RIGHT));
}