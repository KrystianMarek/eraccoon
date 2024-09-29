 #include "CytronMotorDriver.h"
 #include "DFRobot_RGBLCD1602.h"

// Define Joystick pins
const int PIN_J_FORWARD = 22;
const int PIN_J_BACK = 25;
const int PIN_J_LEFT = 24;
const int PIN_J_RIGHT = 23;

const int MAX_SPEED = 128;
const int MIN_SPEED = 50;

// LCD
const int colorR = 0;
const int colorG = 128;
const int colorB = 0;

// Define the motor driver pins
CytronMD motor_fl(PWM_PWM, 2, 3);   
CytronMD motor_rl(PWM_PWM, 4, 5);
CytronMD motor_fr(PWM_PWM, 6, 7);   
CytronMD motor_rr(PWM_PWM, 8, 9);

DFRobot_RGBLCD1602 lcd(0x2D, 16, 2);

void setup_joystick() {
  for(int i=22;i<26;i++)
    pinMode(i,INPUT);
}

void setup() {
  lcd.init();
  lcd.clear();
  lcd.setRGB(colorR, colorG, colorB);
    
  // Print a message to the LCD.
  lcd.print("hello!");
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

/*

const int DESIRED_SPEED = 255; // Maximum motor speed
const unsigned long ACCELERATION_TIME = 1000; // Time to reach full speed in milliseconds

unsigned long lastUpdateTime = 0;
int currentSpeed = 0;

void controlMotors() {
  unsigned long currentTime = millis();
  unsigned long deltaTime = currentTime - lastUpdateTime;
  lastUpdateTime = currentTime;

  bool forward = digitalRead(J_FORWARD);
  bool backward = digitalRead(J_BACKWARD);
  bool left = digitalRead(J_LEFT);
  bool right = digitalRead(J_RIGHT);

  int targetSpeed = 0;
  if (forward || backward || left || right) {
    targetSpeed = DESIRED_SPEED;
  }

  // Calculate speed change
  int speedChange = (int)((float)DESIRED_SPEED * deltaTime / ACCELERATION_TIME);
  
  // Accelerate or decelerate
  if (targetSpeed > currentSpeed) {
    currentSpeed = min(currentSpeed + speedChange, DESIRED_SPEED);
  } else if (targetSpeed < currentSpeed) {
    currentSpeed = max(currentSpeed - speedChange, 0);
  }

  // Set motor speeds based on joystick input
  if (forward) {
    motor_fl.setSpeed(currentSpeed);
    motor_fr.setSpeed(currentSpeed);
    motor_rl.setSpeed(currentSpeed);
    motor_rr.setSpeed(currentSpeed);
  } else if (backward) {
    motor_fl.setSpeed(-currentSpeed);
    motor_fr.setSpeed(-currentSpeed);
    motor_rl.setSpeed(-currentSpeed);
    motor_rr.setSpeed(-currentSpeed);
  } else if (left) {
    motor_fl.setSpeed(-currentSpeed);
    motor_fr.setSpeed(currentSpeed);
    motor_rl.setSpeed(-currentSpeed);
    motor_rr.setSpeed(currentSpeed);
  } else if (right) {
    motor_fl.setSpeed(currentSpeed);
    motor_fr.setSpeed(-currentSpeed);
    motor_rl.setSpeed(currentSpeed);
    motor_rr.setSpeed(-currentSpeed);
  } else {
    // No input, stop all motors
    motor_fl.setSpeed(0);
    motor_fr.setSpeed(0);
    motor_rl.setSpeed(0);
    motor_rr.setSpeed(0);
  }
}

*/