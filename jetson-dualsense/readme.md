# dualsense interface

On ubuntu joystick can be tested with `jstest-gtk`

https://github.com/flok/pydualsense

```shell
sudo cp 70-ps5-controller.rules /etc/udev/rules.d
sudo udevadm control --reload-rules
sudo udevadm trigger
```