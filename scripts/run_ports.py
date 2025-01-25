import serial.tools.list_ports

ports = serial.tools.list_ports.comports()

# Just list out all the COM ports for convenience
for port, desc, hwid in sorted(ports):
    print(f"{port}: {desc} [{hwid}]")
