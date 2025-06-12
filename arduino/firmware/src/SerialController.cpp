//
// Created for serial communication with PC
//

#include "SerialController.h"

SerialController::SerialController() {
    this->inputString = "";
    this->commandReady = false;
    // Serial.begin() is called in main.cpp setup()
}

SerialCommand SerialController::getCommand() {
    SerialCommand cmd;
    cmd.valid = false;

    if (hasCommand()) {
        cmd = parseCommand(inputString);
        inputString = ""; // Clear the command
        commandReady = false;
    }

    return cmd;
}

void SerialController::sendSensorData(DistanceSensors *sensors) {
    // Check distances and send data
    sensors->checkDistance();

    // Send sensor data in JSON format for easy parsing
    Serial.print("{\"sensors\":{");
    Serial.print("\"front_left\":");
    Serial.print(sensors->getFrontLeftDistance());
    Serial.print(",\"front_right\":");
    Serial.print(sensors->getFrontRightDistance());
    Serial.print(",\"rear_left\":");
    Serial.print(sensors->getRearLeftDistance());
    Serial.print(",\"rear_right\":");
    Serial.print(sensors->getRearRightDistance());
    Serial.print(",\"front_collision\":");
    Serial.print(sensors->frontCollison() ? "true" : "false");
    Serial.print(",\"rear_collision\":");
    Serial.print(sensors->rearCollison() ? "true" : "false");
    Serial.println("}}");
}

bool SerialController::hasCommand() {
    // Check for incoming serial data

        while (Serial.available()) {
        char inChar = (char)Serial.read();

        if (inChar == '\n') {
            commandReady = true;
            Serial.print("RECEIVED: '");
            Serial.print(inputString);
            Serial.println("'");
            break;
        } else if (inChar != '\r') { // Ignore carriage return
            inputString += inChar;
        }
    }

    return commandReady;
}

SerialCommand SerialController::parseCommand(String command) {
    SerialCommand cmd;
    cmd.valid = false;
    cmd.direction = STOP;
    cmd.speed = 0;

    command.trim();

    // Expected format: "DIRECTION:SPEED" (e.g., "FORWARD:60" or "STOP:0")
    int colonIndex = command.indexOf(':');
    if (colonIndex > 0) {
        String dirStr = command.substring(0, colonIndex);
        String speedStr = command.substring(colonIndex + 1);

        cmd.direction = parseDirection(dirStr);
        cmd.speed = speedStr.toInt();

        // Validate speed range
        if (cmd.speed >= 0 && cmd.speed <= 255) {
            cmd.valid = true;
            Serial.print("PARSED: ");
            Serial.print(dirStr);
            Serial.print(":");
            Serial.print(cmd.speed);
            Serial.print(" -> ");
            Serial.println(cmd.direction);
        } else {
            Serial.print("INVALID SPEED: ");
            Serial.println(cmd.speed);
        }
    } else {
        Serial.print("NO COLON FOUND IN: '");
        Serial.print(command);
        Serial.println("'");
    }

    return cmd;
}

MotionDirection SerialController::parseDirection(String dir) {
    dir.toUpperCase();

    if (dir == "FORWARD") return FORWARD;
    else if (dir == "BACKWARD") return BACKWARD;
    else if (dir == "LEFT") return LEFT;
    else if (dir == "RIGHT") return RIGHT;
    else if (dir == "FORWARD_LEFT") return FORWARD_LEFT;
    else if (dir == "FORWARD_RIGHT") return FORWARD_RIGHT;
    else if (dir == "BACKWARD_LEFT") return BACKWARD_LEFT;
    else if (dir == "BACKWARD_RIGHT") return BACKWARD_RIGHT;
    else if (dir == "RESET") {
        // Special reset command - will be handled by RobotController
        Serial.println("RESET COMMAND RECEIVED");
        return ROBOT_RESET;
    }
    else if (dir == "KEEPALIVE") {
        // Keep-alive command to prevent auto-reboot
        Serial.println("💓 KEEPALIVE RECEIVED");
        return KEEPALIVE_CMD; // Special command type that doesn't reset activity timer
    }
    else return STOP;
}