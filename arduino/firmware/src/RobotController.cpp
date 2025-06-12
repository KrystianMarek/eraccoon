//
// Created to orchestrate robot control from multiple sources
//

#include "RobotController.h"

RobotController::RobotController(
    MotorController *motorController,
    JoystickController *joystickController,
    SerialController *serialController,
    DistanceSensors *distanceSensors,
    MyLCD *lcd
) {
    this->motorController = motorController;
    this->joystickController = joystickController;
    this->serialController = serialController;
    this->distanceSensors = distanceSensors;
    this->lcd = lcd;

    // Send sensor data every 500ms to PC (reduce frequency to avoid flooding)
    this->sensorReportTicker = new Ticker(500);

    // Update LCD every 200ms
    this->lcdUpdateTicker = new Ticker(200);

    // Initialize serial command tracking
    this->lastSerialCommand.valid = false;
    this->lastSerialCommandTime = 0;
    this->lastSerialActivity = millis();

    // Initialize safety system state
    this->wasPreviouslyBlocked = false;
}

void RobotController::update() {
    // Send sensor data periodically to PC
    if (sensorReportTicker->tick()) {
        serialController->sendSensorData(distanceSensors);
    }

    // Update LCD display periodically
    if (lcdUpdateTicker->tick()) {
        updateLCDDisplay();
    }

            // Smart disconnection detection and auto-reboot logic
    static unsigned long lastSerialActivity = 0;
    static bool serialWasActive = false;
    static unsigned long lastAliveMessage = 0;
    static unsigned long connectionStartTime = 0;
    unsigned long currentTime = millis();

    // Send periodic alive message
    if (currentTime - lastAliveMessage > 30000) { // Every 30 seconds
        Serial.println("💓 ALIVE: Arduino responsive");
        lastAliveMessage = currentTime;
    }

    // Check for new serial commands
    SerialCommand cmd = serialController->getCommand();

    // Track serial activity - any command or available data means connection is active
    // BUT: KEEPALIVE commands don't count as "real" activity for timeout purposes
    if (cmd.valid || Serial.available() > 0) {
        if (!serialWasActive) {
            Serial.println("🔌 SERIAL CONNECTED: External controller detected");
            serialWasActive = true;
            connectionStartTime = currentTime;
        }

        // Only reset activity timer for non-keepalive commands
        if (!cmd.valid || cmd.direction != KEEPALIVE_CMD) {
            lastSerialActivity = currentTime;
        }
    }

        // Check for actual serial port disconnection every 500ms
    static unsigned long lastDisconnectCheck = 0;
    if (currentTime - lastDisconnectCheck > 500) {
        lastDisconnectCheck = currentTime;
        // Temporarily disabled aggressive disconnection reboot for debugging
        /*
        // If we had an active connection but can no longer write to serial, reboot immediately
        if (serialWasActive && !Serial.availableForWrite()) {
            Serial.println("🔌 SERIAL PORT DISCONNECTED: Port no longer writable");
            Serial.println("🔄 AUTO-REBOOT: Immediate restart for clean state...");
            // Trigger immediate reboot by jumping to bootloader or reset vector
            // This is a hard reset that ensures clean state for new connection
            asm volatile ("jmp 0");
        }
        */
    }

    // Only check for timeout after connection has been stable for at least 5 seconds
    // This prevents rebooting during initial handshake or rapid command sequences
    if (serialWasActive && (currentTime - connectionStartTime > 5000)) {
        // Auto-reboot logic: if we had serial activity but haven't seen any for 5 seconds, reboot
        // Temporarily extending timeout to 10 seconds for debugging
        if (currentTime - lastSerialActivity > 10000) {
            Serial.println("🔄 AUTO-REBOOT: Restarting Arduino for clean state...");
            // Trigger immediate reboot
            asm volatile ("jmp 0");
        }
    }

    if (cmd.valid) {
        // Check if it's a reset command
        if (cmd.direction == ROBOT_RESET) {
            resetAllStates();
            return;
        }

        // Check if it's a keepalive command
        if (cmd.direction == KEEPALIVE_CMD) {
            Serial.println("💓 KEEPALIVE processed - no motor action");
            return; // Don't process as motor command
        }

        // New serial command received
        lastSerialCommand = cmd;
        lastSerialCommandTime = millis();
        Serial.print("🤖 NEW SERIAL CMD: ");
        Serial.print(cmd.direction);
        Serial.print(" at speed ");
        Serial.println(cmd.speed);
        motorController->move(cmd.direction, cmd.speed);

        // If it's a STOP command, execute it but don't persist it - let joystick take over immediately
        if (cmd.direction == STOP) {
            lastSerialCommand.valid = false;
            Serial.println("🛑 STOP CMD - EXECUTED, NOT PERSISTING");
        }
    } else if (hasActiveSerialCommand()) {
        // Continue executing the last serial command, but with throttled debug output
        static unsigned long lastContinuingDebug = 0;
        if (currentTime - lastContinuingDebug > 500) { // Debug every 500ms instead of every loop
            Serial.print("🤖 CONTINUING: ");
            Serial.print(lastSerialCommand.direction);
            Serial.print(" at speed ");
            Serial.print(lastSerialCommand.speed);
            Serial.print(" (");
            Serial.print(currentTime - lastSerialCommandTime);
            Serial.println("ms elapsed)");
            lastContinuingDebug = currentTime;
        }
        motorController->move(lastSerialCommand.direction, lastSerialCommand.speed);
    } else {
        // No active serial command, use joystick control
        static unsigned long lastJoystickDebugTime = 0;
        if (currentTime - lastJoystickDebugTime > 2000) { // Debug every 2 seconds
            Serial.println("🕹️  USING JOYSTICK CONTROL");
            lastJoystickDebugTime = currentTime;
        }
        handleJoystickControl();
    }
}

void RobotController::handleJoystickControl() {
    static bool lastJoystickActive = false;
    static MotionDirection lastDirection = STOP;
    static unsigned long lastJoystickDebugTime = 0;

    // Check raw joystick pins for debugging
    bool forward = digitalRead(22);
    bool back = digitalRead(25);
    bool left = digitalRead(24);
    bool right = digitalRead(23);

    bool isCurrentlyActive = joystickController->isActive();

    // Enhanced debugging for joystick state
    unsigned long currentTime = millis();
    if (currentTime - lastJoystickDebugTime > 1000) { // Debug every second
        Serial.print("🕹️  JOYSTICK DEBUG - ");
        Serial.print("Active:");
        Serial.print(isCurrentlyActive ? "YES" : "NO");
        Serial.print(" Pins F:");
        Serial.print(forward);
        Serial.print(" B:");
        Serial.print(back);
        Serial.print(" L:");
        Serial.print(left);
        Serial.print(" R:");
        Serial.println(right);
        lastJoystickDebugTime = currentTime;
    }

    if (isCurrentlyActive) {
        JoyState joyState = joystickController->getJoystickState();

        // Only debug when state changes
        if (!lastJoystickActive || joyState.direction != lastDirection) {
            Serial.print("🎮 JOYSTICK ACTIVE: dir=");
            Serial.print(joyState.direction);
            Serial.print(" speed=");
            Serial.println(joyState.speed);
        }

        lastJoystickActive = true;
        lastDirection = joyState.direction;

        // Apply safety checks for joystick control
        if (isMovementSafe(joyState.direction)) {
            motorController->move(joyState.direction, joyState.speed);
        } else {
            // Safety system is blocking movement - provide detailed feedback
            bool frontBlocked = distanceSensors->frontCollison();
            bool rearBlocked = distanceSensors->rearCollison();

            Serial.print("🚫 JOYSTICK SAFETY BLOCK - dir:");
            Serial.print(joyState.direction);
            Serial.print(" front:");
            Serial.print(frontBlocked ? "BLOCKED" : "CLEAR");
            Serial.print(" rear:");
            Serial.println(rearBlocked ? "BLOCKED" : "CLEAR");

            // Change LCD color to red when blocked
            lcd->setColor(255, 0, 0); // Red for danger

            motorController->stop();
        }
    } else {
        if (lastJoystickActive) {
            Serial.println("🕹️  JOYSTICK INACTIVE - STOPPING");
        }
        lastJoystickActive = false;
        lastDirection = STOP;
        motorController->stop();
    }
}

bool RobotController::hasActiveSerialCommand() {
    if (!lastSerialCommand.valid) {
        return false;
    }

    unsigned long currentTime = millis();
    bool isActive = (currentTime - lastSerialCommandTime) < SERIAL_COMMAND_TIMEOUT;

    if (!isActive) {
        // Command has expired, invalidate it
        lastSerialCommand.valid = false;
        Serial.println("SERIAL CMD EXPIRED - CLEARING BUFFER");

        // Clear any leftover serial data
        while (Serial.available()) {
            Serial.read();
        }
    }

    return isActive;
}

void RobotController::updateLCDDisplay() {
    // Update sensor readings
    distanceSensors->checkDistance();

    bool frontBlocked = distanceSensors->frontCollison();
    bool rearBlocked = distanceSensors->rearCollison();

    static bool lastFrontBlocked = false;
    static bool lastRearBlocked = false;
    static unsigned long lastResetTime = 0;
    static bool hasSeenReset = false;

            // Check if we should force update after reset (show current status instead of SYSTEM RESET)
    unsigned long currentTime = millis();
    bool shouldForceUpdate = false;

    // Only force update once after reset, don't keep doing it
    if (!hasSeenReset && lastSerialCommand.valid == false && lastSerialCommandTime == 0) {
        // We've seen a reset condition - but only trigger once
        hasSeenReset = true;
        lastResetTime = currentTime;
        shouldForceUpdate = true;
    } else if (hasSeenReset && (currentTime - lastResetTime > 2000)) {
        // 2 seconds after reset, do one final update and stop forcing
        shouldForceUpdate = true;
        hasSeenReset = false; // Stop the force update cycle
    }

    // Only update LCD when status actually changes or we need to force update
    bool actuallyChanged = (frontBlocked != lastFrontBlocked || rearBlocked != lastRearBlocked);
    if (actuallyChanged || shouldForceUpdate) {
        if (actuallyChanged) {
            Serial.println("📺 LCD: Sensor status changed - updating display");
        } else {
            Serial.println("📺 LCD: Force update after reset");
        }

                        if (frontBlocked || rearBlocked) {
            // Set color to red for obstacles
            lcd->setColor(255, 0, 0);
            lcd->clear();
            lcd->print("OBSTACLE:");
            lcd->setCursor(0, 1);

            if (frontBlocked && rearBlocked) {
                lcd->print("FRONT & REAR");
            } else if (frontBlocked) {
                lcd->print("FRONT BLOCKED");
            } else if (rearBlocked) {
                lcd->print("REAR BLOCKED");
            }

            Serial.print("LCD: OBSTACLE - Front:");
            Serial.print(frontBlocked ? "BLOCKED" : "CLEAR");
            Serial.print(" Rear:");
            Serial.println(rearBlocked ? "BLOCKED" : "CLEAR");

            // Mark that we were blocked (for clearing stuck states later)
            wasPreviouslyBlocked = true;
                } else {
            // Set color to green for all clear
            lcd->setColor(0, 255, 0);
            lcd->clear();
            lcd->print("ALL CLEAR");
            lcd->setCursor(0, 1);

            if (hasActiveSerialCommand()) {
                lcd->print("SERIAL MODE");
            } else if (joystickController->isActive()) {
                lcd->print("JOYSTICK MODE");
            } else {
                lcd->print("READY");
            }

            Serial.println("LCD: ALL CLEAR - Safety system unlocked");

            // Clear any potential stuck serial commands when path is clear
            if (wasPreviouslyBlocked) {
                Serial.println("CLEARING STUCK STATES - Path now clear");
                // Clear any lingering serial data
                while (Serial.available()) {
                    Serial.read();
                }
                lastSerialCommand.valid = false;
                wasPreviouslyBlocked = false;
            }
        }

        lastFrontBlocked = frontBlocked;
        lastRearBlocked = rearBlocked;
    }
}

bool RobotController::isMovementSafe(MotionDirection direction) {
    static unsigned long lastSensorDebug = 0;
    unsigned long currentTime = millis();

    // Always check current sensor status for real-time safety
    distanceSensors->checkDistance();
    bool frontBlocked = distanceSensors->frontCollison();
    bool rearBlocked = distanceSensors->rearCollison();

    // Debug sensor values occasionally
    if (currentTime - lastSensorDebug > 3000) {
        Serial.print("SENSOR DEBUG - FL:");
        Serial.print(distanceSensors->getFrontLeftDistance());
        Serial.print(" FR:");
        Serial.print(distanceSensors->getFrontRightDistance());
        Serial.print(" RL:");
        Serial.print(distanceSensors->getRearLeftDistance());
        Serial.print(" RR:");
        Serial.print(distanceSensors->getRearRightDistance());
        Serial.print(" FrontBlock:");
        Serial.print(frontBlocked);
        Serial.print(" RearBlock:");
        Serial.println(rearBlocked);
        lastSensorDebug = currentTime;
    }

    switch(direction) {
        case FORWARD:
        case FORWARD_LEFT:
        case FORWARD_RIGHT:
            if (frontBlocked) {
                Serial.println("MOVEMENT BLOCKED: Front obstacle detected");
                return false;
            }
            return true;

        case BACKWARD:
        case BACKWARD_LEFT:
        case BACKWARD_RIGHT:
            if (rearBlocked) {
                Serial.println("MOVEMENT BLOCKED: Rear obstacle detected");
                return false;
            }
            return true;

        case LEFT:
        case RIGHT:
        case STOP:
        case ROBOT_RESET:
        default:
            return true; // Side movements, stop, and reset are always safe
    }
}

void RobotController::resetAllStates() {
    Serial.println("🔄 RESET: Clearing all states");

    // Stop all motors immediately
    motorController->stop();

    // Clear serial command state completely
    lastSerialCommand.valid = false;
    lastSerialCommand.direction = STOP;
    lastSerialCommand.speed = 0;
    lastSerialCommandTime = 0;
    lastSerialActivity = millis(); // Reset activity tracking

    // Clear any stuck serial data aggressively
    while (Serial.available()) {
        Serial.read();
    }
    // Give the serial buffer time to clear
    delay(10);
    while (Serial.available()) {
        Serial.read();
    }

    // Reset safety state
    wasPreviouslyBlocked = false;

        // Force a complete system state refresh
    // This ensures all controllers start fresh
    Serial.println("🔄 RESET: Forcing complete state refresh");

    // Reset LCD to default state
    lcd->setColor(0, 255, 0); // Green
    lcd->clear();
    lcd->print("SYSTEM RESET");
    lcd->setCursor(0, 1);
    lcd->print("READY");

    // Give some time for everything to settle
    delay(100);

    Serial.println("🔄 RESET: All states cleared, system ready");
}