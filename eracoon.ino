
/*!
* eracoon
*
* @version  V0.1
*/
const int E1 = 3; ///<Motor1 Speed
const int E2 = 11;///<Motor2 Speed
const int E3 = 5; ///<Motor3 Speed
const int E4 = 6; ///<Motor4 Speed

const int M1 = 4; //Back left
const int M2 = 12;//Back right
const int M3 = 8; //Forward right
const int M4 = 7; //Forward left

const int J_FORWARD = 25;
const int J_BACK = 22;
const int J_LEFT = 24;
const int J_RIGHT = 23;

const int MAX_SPEED = 100;
const int MIN_SPEED = 50;

int buttonState = 0; 

void M1_advance(char Speed) ///<Motor1 Advance
{
 digitalWrite(M1,LOW);
 analogWrite(E1,Speed);
}
void M2_advance(char Speed) ///<Motor2 Advance
{
 digitalWrite(M2,HIGH);
 analogWrite(E2,Speed);
}
void M3_advance(char Speed) ///<Motor3 Advance
{
 digitalWrite(M3,LOW);
 analogWrite(E3,Speed);
}
void M4_advance(char Speed) ///<Motor4 Advance
{
 digitalWrite(M4,HIGH);
 analogWrite(E4,Speed);
}

void M1_back(char Speed) ///<Motor1 Back off
{
 digitalWrite(M1,HIGH);
 analogWrite(E1,Speed);
}
void M2_back(char Speed) ///<Motor2 Back off
{
 digitalWrite(M2,LOW);
 analogWrite(E2,Speed);
}
void M3_back(char Speed) ///<Motor3 Back off
{
 digitalWrite(M3,HIGH);
 analogWrite(E3,Speed);
}
void M4_back(char Speed) ///<Motor4 Back off
{
 digitalWrite(M4,LOW);
 analogWrite(E4,Speed);
}


void setup() {
  for(int i=3;i<9;i++)
    pinMode(i,OUTPUT);
  for(int i=11;i<13;i++)
    pinMode(i,OUTPUT);
  for(int i=22;i<26;i++)
    pinMode(i,INPUT);
}

void j_ride(int jForward, int jBackward, int jLeft, int jRight) {
  //stop
  if (jForward == LOW && jBackward == LOW && jLeft == LOW && jRight == LOW) {
    M1_advance(0);
    M2_advance(0);
    M3_advance(0);
    M4_advance(0);
  }
  //forward
  if (jForward == HIGH && jBackward == LOW && jLeft == LOW && jRight == LOW) {
    M1_advance(MAX_SPEED);
    M2_advance(MAX_SPEED);
    M3_advance(MAX_SPEED);
    M4_advance(MAX_SPEED);
  }
  //back
  if (jForward == LOW && jBackward == HIGH && jLeft == LOW && jRight == LOW) {
    M1_back(MAX_SPEED);
    M2_back(MAX_SPEED);
    M3_back(MAX_SPEED);
    M4_back(MAX_SPEED);
  }
  //dead left 
  if (jForward == LOW && jBackward == LOW && jLeft == HIGH && jRight == LOW) {
    M1_back(MAX_SPEED);
    M2_advance(MAX_SPEED);
    M3_advance(MAX_SPEED);
    M4_back(MAX_SPEED);
  }
  //dead right
  if (jForward == LOW && jBackward == LOW && jLeft == LOW && jRight == HIGH) {
    M1_advance(MAX_SPEED);
    M2_back(MAX_SPEED);
    M3_back(MAX_SPEED);
    M4_advance(MAX_SPEED);
  }
}

void loop() {
  j_ride(digitalRead(J_FORWARD), digitalRead(J_BACK), digitalRead(J_LEFT), digitalRead(J_RIGHT));
}