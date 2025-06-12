#! /usr/bin/env python3

import pygame

pygame.init()
pygame.joystick.init()
joystick = pygame.joystick.Joystick(0)
joystick.init()

print(f"Joystick name: {joystick.get_name()}")  # Should print "Sony Interactive Entertainment Wireless Controller"
print(f"Number of axes: {joystick.get_numaxes()}")  # Should print 6
print(f"Number of buttons: {joystick.get_numbuttons()}")  # Should print 13

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.JOYAXISMOTION:
            print(f"Axis {event.axis} moved to {event.value}")
        elif event.type == pygame.JOYBUTTONDOWN:
            print(f"Button {event.button} pressed")

pygame.quit()