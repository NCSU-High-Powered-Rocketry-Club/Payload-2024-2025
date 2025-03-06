import serial
import time
import struct
from payload.constants import ARDUINO_BAUD_RATE, PACKET_START_MARKER
from collections import deque

def detect_and_read_packets(port='/dev/ttyUSB1', baud_rate=ARDUINO_BAUD_RATE):
    # Start flag configuration
    START_FLAG = PACKET_START_MARKER
    START_FLAG_LEN = len(START_FLAG)
    
    # DataPacket structure size (in bytes)
    PACKET_SIZE = 84
    
    # Initialize serial port
    ser = serial.Serial(port, baud_rate, timeout=1)
    print(f"Connected to {port} at {baud_rate} baud")
    print(f"Monitoring for start flag: 0x{START_FLAG.hex().upper()}")
    
    # Initialize rolling buffer for detecting start flag
    rolling_buffer = deque(maxlen=START_FLAG_LEN)
    
    # Counter for detected packets
    packet_count = 0
    
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
                        # Start flag detected
                        packet_count += 1
                        timestamp = time.strftime('%H:%M:%S.%f')[:-3]
                        print(f"[{timestamp}] Start flag detected! (#{packet_count})")
                        
                        # Read the full 84-byte packet
                        packet_data = ser.read(PACKET_SIZE)
                        
                        # Check if we got all the expected data
                        if len(packet_data) == PACKET_SIZE:
                            # Parse the packet using struct
                            # Format: 21 floats = 21 * 4 bytes = 84 bytes
                            data = struct.unpack('<21f', packet_data)
                            
                            # Extract individual fields
                            packet = {
                                'timestamp': data[0],
                                'voltage': data[1],
                                'temperature': data[2],
                                'pressure': data[3],
                                'altitude': data[4],
                                'comp_accel': {'x': data[5], 'y': data[6], 'z': data[7]},
                                'gyro': {'x': data[8], 'y': data[9], 'z': data[10]},
                                'magnetic': {'x': data[11], 'y': data[12], 'z': data[13]},
                                'quaternion': {'w': data[14], 'x': data[15], 'y': data[16], 'z': data[17]},
                                'gps': {'lat': data[18], 'long': data[19], 'alt': data[20]}
                            }
                            
                            # Print packet information
                            print(f"Packet #{packet_count} Data:")
                            print(f"  Time: {packet['timestamp']:.3f}s")
                            print(f"  Voltage: {packet['voltage']:.2f}V")
                            print(f"  Temperature: {packet['temperature']:.1f}°C")
                            print(f"  Pressure: {packet['pressure']:.2f} hPa")
                            print(f"  Altitude: {packet['altitude']:.2f} m")
                            print(f"  Accelerometer: X={packet['comp_accel']['x']:.2f}, Y={packet['comp_accel']['y']:.2f}, Z={packet['comp_accel']['z']:.2f} g")
                            print(f"  Gyroscope: X={packet['gyro']['x']:.2f}, Y={packet['gyro']['y']:.2f}, Z={packet['gyro']['z']:.2f} deg/s")
                            print(f"  Magnetometer: X={packet['magnetic']['x']:.2f}, Y={packet['magnetic']['y']:.2f}, Z={packet['magnetic']['z']:.2f} uT")
                            print(f"  Quaternion: W={packet['quaternion']['w']:.3f}, X={packet['quaternion']['x']:.3f}, Y={packet['quaternion']['y']:.3f}, Z={packet['quaternion']['z']:.3f}")
                            print(f"  GPS: Lat={packet['gps']['lat']:.6f}, Long={packet['gps']['long']:.6f}, Alt={packet['gps']['alt']:.2f} m")
                            print("---------------------")
                        else:
                            print(f"Error: Incomplete packet data. Expected {PACKET_SIZE} bytes, got {len(packet_data)} bytes.")
                            
                            # Clear any remaining data to resynchronize
                            ser.reset_input_buffer()
            else:
                # No data available, sleep briefly to avoid CPU spinning
                time.sleep(0.01)
                
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
        print(f"Total packets detected and processed: {packet_count}")
    finally:
        ser.close()
        print("Serial port closed")

if __name__ == "__main__":
    # You can modify these parameters based on your setup
    detect_and_read_packets(port='/dev/ttyUSB1')