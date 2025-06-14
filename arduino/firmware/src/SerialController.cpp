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
    cmd.type = INVALID_COMMAND;

    if (hasCommand()) {
        cmd = parseCommand(inputString);
        inputString = ""; // Clear the command
        commandReady = false;
    }

    return cmd;
}

bool SerialController::sendSensorData(DistanceSensors *sensors) {
    // Check distances and send data
    sensors->checkDistance();

    // Send sensor data in JSON format for easy parsing
    // Always attempt to send - if connection is broken, watchdog will handle it
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

    // Always return true - let watchdog handle connection failures
    return true;
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
    command.trim();

    // Check if it's a JSON command (starts with '{')
    if (command.startsWith("{")) {
        return parseJsonCommand(command);
    } else {
        // Legacy command format: "DIRECTION:SPEED"
        return parseLegacyCommand(command);
    }
}

SerialCommand SerialController::parseJsonCommand(String command) {
    SerialCommand cmd;
    cmd.valid = false;
    cmd.type = INVALID_COMMAND;
    cmd.direction = STOP;
    cmd.speed = 0;
    // Initialize motor speeds to 0
    for (int i = 0; i < 4; i++) {
        cmd.motor_speeds[i] = 0;
    }

    // Parse JSON
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, command);

    if (error) {
        Serial.print("JSON PARSE ERROR: ");
        Serial.println(error.c_str());
        return cmd;
    }

    // Check command type
    const char* type = doc["type"];
    if (!type) {
        Serial.println("MISSING TYPE FIELD IN JSON");
        return cmd;
    }

    if (strcmp(type, "tank") == 0) {
        // Tank command format: {"type": "tank", "command": "FORWARD", "value": 60}
        const char* commandStr = doc["command"];
        int value = doc["value"];

        if (!commandStr) {
            Serial.println("MISSING COMMAND FIELD IN TANK JSON");
            return cmd;
        }

        cmd.type = TANK_COMMAND;
        cmd.direction = parseDirection(String(commandStr));
        cmd.speed = value;

        // Validate speed range
        if (cmd.speed >= 0 && cmd.speed <= 255) {
            cmd.valid = true;
            Serial.print("PARSED TANK JSON: ");
            Serial.print(commandStr);
            Serial.print(":");
            Serial.print(cmd.speed);
            Serial.print(" -> ");
            Serial.println(cmd.direction);
        } else {
            Serial.print("INVALID SPEED IN TANK JSON: ");
            Serial.println(cmd.speed);
        }

    } else if (strcmp(type, "mecanum") == 0) {
        // Mecanum command format: {"type": "mecanum", "motors": {"left_front": -127, "left_rear": 127, "right_front": 127, "right_rear": -127}}
        JsonObject motors = doc["motors"];
        if (!motors) {
            Serial.println("MISSING MOTORS FIELD IN MECANUM JSON");
            return cmd;
        }

        // Extract motor speeds
        cmd.motor_speeds[0] = motors["left_front"] | 0;   // left_front
        cmd.motor_speeds[1] = motors["left_rear"] | 0;    // left_rear
        cmd.motor_speeds[2] = motors["right_front"] | 0;  // right_front
        cmd.motor_speeds[3] = motors["right_rear"] | 0;   // right_rear

        // Validate motor speed ranges (-255 to 255)
        bool valid_speeds = true;
        for (int i = 0; i < 4; i++) {
            if (cmd.motor_speeds[i] < -255 || cmd.motor_speeds[i] > 255) {
                valid_speeds = false;
                break;
            }
        }

        if (valid_speeds) {
            cmd.type = MECANUM_COMMAND;
            cmd.valid = true;
            Serial.print("PARSED MECANUM JSON: LF:");
            Serial.print(cmd.motor_speeds[0]);
            Serial.print(" LR:");
            Serial.print(cmd.motor_speeds[1]);
            Serial.print(" RF:");
            Serial.print(cmd.motor_speeds[2]);
            Serial.print(" RR:");
            Serial.println(cmd.motor_speeds[3]);
        } else {
            Serial.println("INVALID MOTOR SPEEDS IN MECANUM JSON (must be -255 to 255)");
        }

    } else {
        Serial.print("UNKNOWN JSON COMMAND TYPE: ");
        Serial.println(type);
    }

    return cmd;
}

SerialCommand SerialController::parseLegacyCommand(String command) {
    SerialCommand cmd;
    cmd.valid = false;
    cmd.type = LEGACY_COMMAND;
    cmd.direction = STOP;
    cmd.speed = 0;
    // Initialize motor speeds to 0
    for (int i = 0; i < 4; i++) {
        cmd.motor_speeds[i] = 0;
    }

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
            Serial.print("PARSED LEGACY: ");
            Serial.print(dirStr);
            Serial.print(":");
            Serial.print(cmd.speed);
            Serial.print(" -> ");
            Serial.println(cmd.direction);
        } else {
            Serial.print("INVALID SPEED IN LEGACY: ");
            Serial.println(cmd.speed);
        }
    } else {
        Serial.print("NO COLON FOUND IN LEGACY: '");
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