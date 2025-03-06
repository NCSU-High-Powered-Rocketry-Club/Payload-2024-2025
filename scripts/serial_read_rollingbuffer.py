import serial
import time
from collections import deque

def detect_start_flags(port='/dev/ttyUSB0', baud_rate=9600):
    # Start flag configuration
    START_FLAG = bytes.fromhex('FFFEFDFC')
    START_FLAG_LEN = len(START_FLAG)
    
    # Initialize serial port
    ser = serial.Serial(port, baud_rate, timeout=1)
    print(f"Connected to {port} at {baud_rate} baud")
    print(f"Monitoring for start flag: 0x{START_FLAG.hex().upper()}")
    
    # Initialize rolling buffer for detecting start flag
    rolling_buffer = deque(maxlen=START_FLAG_LEN)
    
    # Counter for detected flags
    flag_count = 0
    
    try:
        while True:
            # Read a byte if available
            if ser.in_waiting > 0:
                byte_data = ser.read(1)
                
                # Add byte to rolling buffer
                rolling_buffer.append(byte_data[0])
                
                # Check if rolling buffer contains start flag
                if len(rolling_buffer) == START_FLAG_LEN:
                    rolling_bytes = bytes(rolling_buffer)
                    if rolling_bytes == START_FLAG:
                        flag_count += 1
                        timestamp = time.strftime('%H:%M:%S.%f')[:-3]
                        print(f"[{timestamp}] Start flag detected! (#{flag_count})")
            else:
                # No data available, sleep briefly to avoid CPU spinning
                time.sleep(0.01)
                
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
        print(f"Total start flags detected: {flag_count}")
    finally:
        ser.close()
        print("Serial port closed")

if __name__ == "__main__":
    # You can modify these parameters based on your setup
    detect_start_flags(port='/dev/ttyUSB0', baud_rate=9600)