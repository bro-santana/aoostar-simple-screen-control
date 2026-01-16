import struct
import argparse
import serial
import serial.tools.list_ports
from PIL import Image, ImageDraw, ImageFont

TARGET_VID = 0x0416 
TARGET_PID = 0x90A1

# --- Protocol Constants ---
# Header Preamble: AA 55 AA 55
PREAMBLE = b'\xAA\x55\xAA\x55'

# LCD ON: Header + 0x0B + 0x00*3
# Bytes: AA 55 AA 55 0B 00 00 00
CMD_LCD_ON = PREAMBLE + b'\x0B\x00\x00\x00'

# LCD OFF: Header + 0x0A + 0x00*3
# Bytes: AA 55 AA 55 0A 00 00 00
CMD_LCD_OFF = PREAMBLE + b'\x0A\x00\x00\x00'

# IMG START: 
# Matches the sequence in 'img_cmd_start' image exactly:
# AA 55 AA 55 05 00 00 00 04 00 0F 2F 00 04 0B 00
# Note: The last 4 bytes (00 04 0B 00) correspond to the total size 721,920 (0xB0400) in Little Endian.
CMD_IMG_START = PREAMBLE + b'\x05\x00\x00\x00\x04\x00\x0F\x2F\x00\x04\x0B\x00'

# CHUNK HEADER: Header + 0x08 + 0x00*3
# Bytes: AA 55 AA 55 08 00 00 00
CMD_CHUNK_HEADER = PREAMBLE + b'\x08\x00\x00\x00'

# IMG END: Header + 0x06 + 0x00*3
# Bytes: AA 55 AA 55 06 00 00 00
CMD_IMG_END = PREAMBLE + b'\x06\x00\x00\x00'

# --- Display Config ---
WIDTH = 960
HEIGHT = 376
TOTAL_BYTES = WIDTH * HEIGHT * 2  # 721,920 bytes
CHUNK_SIZE = 47
CHUNK_COUNT = TOTAL_BYTES // CHUNK_SIZE #15,360 bytes

def find_serial_port():
    """
    Finds the serial port name for the device's USB Vendor ID and Product ID.

    Returns:
        str or None: The name of the serial port (e.g., 'COM3' or '/dev/ttyUSB0'), 
                     or None if not found.
    """
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == TARGET_VID and port.pid == TARGET_PID:
            return port.device
    return None

def check_ack(ser, context=""):
    """Reads one byte and ensures it is 'A'."""
    resp = ser.read(1)
    if resp != b'A':
        raise IOError(f"NACK or Timeout in {context}. Received: {resp}")

def lcd_on(ser):
    ser.write(CMD_LCD_ON)
    check_ack(ser, "lcd_on")

def lcd_off(ser):
    ser.write(CMD_LCD_OFF)
    check_ack(ser, "lcd_off")

def _image_to_rgb565(img):
    """
    Converts any image to the specific 960x376 RGB565 byte array.
    """
    
    # Force RGB
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Resize to exact display dimensions
    # Using LANCZOS for high-quality downsampling
    img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    
    pixels = list(img.get_flattened_data())
    data = bytearray()
    
    for r, g, b in pixels:
        # Convert to RGB565: R(5bits) G(6bits) B(5bits)
        r5 = (r >> 3) & 0x1F
        g6 = (g >> 2) & 0x3F
        b5 = (b >> 3) & 0x1F
        rgb = (r5 << 11) | (g6 << 5) | b5
        
        # Append as Little Endian (lower byte first)
        data.extend(struct.pack('<H', rgb))
        
    return data

def send_image_data(ser, img_data):
    """
    Sends an image using the specific 47-chunk protocol.
    """
    
    if len(img_data) != TOTAL_BYTES:
        raise ValueError(f"Image data size mismatch. Expected {TOTAL_BYTES}, got {len(img_data)}")

    print("Sending Start Command...")
    ser.write(CMD_IMG_START)
    check_ack(ser, "img_cmd_start")

    print(f"Sending {len(img_data)} bytes in {CHUNK_COUNT} chunks (Chunk Size: {CHUNK_SIZE})...")
    
    for i in range(CHUNK_COUNT):
        offset = i * CHUNK_SIZE
        chunk = img_data[offset : offset + CHUNK_SIZE]
        
        # [CMD_CHUNK_HEADER] + [OFFSET (u32 LE)] + [CHUNK DATA]
        offset_bytes = struct.pack('<I', offset)
        packet = CMD_CHUNK_HEADER + offset_bytes + chunk
        
        ser.write(packet)
        check_ack(ser, f"chunk_{i}")
        
        print(f"\rProgress: {i+1}/{CHUNK_COUNT}", end='')

    print("\nAll chunks sent.")

    print("Sending End Command...")
    ser.write(CMD_IMG_END)
    check_ack(ser, "img_cmd_end")
    print("Done.")

def send_image(ser, image_path):
    """
    """
    print("Converting image...")

    img = Image.open(image_path)
    img_data = _image_to_rgb565(img)
    send_image_data(ser,img_data)


def send_text(ser,text):
    #try:
    #    image = Image.open("input_image.jpg")
    #except FileNotFoundError:
    #    # Create a new image if the file isn't found for the example to work
    #    image = Image.new("RGB", (WIDTH, HEIGHT), color = 'black')

    color = "white"
    color_bg = "black"
    position = (50, 50) 

    image = Image.new("RGB", (WIDTH, HEIGHT), color=color_bg)

    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("fonts/Mx437_IBM_PS-55_re.ttf", 48)
    except IOError:
        font = None # Use default font if not available

    draw.text(position, text, fill=color, font=font)

    #draw.text(position, "CPU Temp:", fill="white", font=font)
    #position = (position[0] + draw.textlength("CPU Temp:", font=font) , position[1])
    #draw.text(position, "99C", fill="red", font=font)
    #position = (50 , position[1] + 48)
    #draw.text(position, "GPU Temp:", fill="white", font=font)
    #position = (position[0] + draw.textlength("GPU Temp:", font=font) , position[1])
    #draw.text(position, "99C", fill="red", font=font)

    img_data = _image_to_rgb565(image)
    send_image_data(ser,img_data)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Basic controls for Aoostar GEM12 PRO MAX or WTR MAX screens")

    parser.add_argument("-e", "--enable", action="store_true",
                        help="Enables screen")
    parser.add_argument("-d", "--disable", action="store_true",
                        help="Disables screen")
    parser.add_argument("-i", "--image", default="",
                        help="Sends image to be displayed")
    parser.add_argument("-t", "--text", default="",
                        help="Sends text to be displayed")

    args = parser.parse_args()

    found_port = find_serial_port()

    if found_port:
        print(f"Device found at port: {found_port}")
    else:
        print(f"Device with VID 0x{target_vid:04X} and PID 0x{target_pid:04X} not found.")

    ser = serial.Serial(found_port,
                        baudrate=1500000,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS,
                        timeout=2.0)
    
    #lcd_on(ser)
    #send_image(ser, "test_image.png")
    #send_text(ser)
    # lcd_off(ser)

    if args.enable:
        lcd_on(ser)
    elif args.disable:
        lcd_off(ser)

    if not args.disable:
        if args.image != "":
            send_image(ser, args.image)
        elif args.text != "":
            send_text(ser, args.text)
    else:
        print("Won't send data with a screen off command")

    ser.close()
