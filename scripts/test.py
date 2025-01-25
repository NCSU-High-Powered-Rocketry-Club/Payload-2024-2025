from payload.hardware.transmitter import Transmitter


t = Transmitter(8, "/home/pi/direwolf.conf")
t.send_message("hello this is a messsage")

import time

time.sleep(10)
t.stop()