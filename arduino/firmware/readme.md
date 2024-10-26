# Development
Switched to PlatformIO + clion.  
There is an [issue](https://github.com/platformio/platform-ststm32/issues/702) with my board on this platform.

Code is compiled on mac, then rsynced to the jetson, and from there uploaded to Arduino.

# build
```shell
pio run
```