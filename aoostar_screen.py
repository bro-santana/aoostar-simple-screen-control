import struct
import argparse
import serial
import serial.tools.list_ports
import json
from PIL import Image, ImageDraw, ImageFont

from hwinfo_data import getHWiNFOData, convertHWiNFODataToAoostarCompatible

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

def send_image(ser, image):
    """
    Sends an image using the specific 47-chunk protocol.
    """
    img_data = _image_to_rgb565(image)
    
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
        
        #print(f"\rProgress: {i+1}/{CHUNK_COUNT}", end='')

    #print("\nAll chunks sent.")
    print("All chunks sent.")

    print("Sending End Command...")
    ser.write(CMD_IMG_END)
    check_ack(ser, "img_cmd_end")
    print("Done.")

def send_image_file(ser, image_path):
    """
    """
    print("Converting image...")

    img = Image.open(image_path)
    send_image(ser,img)


def send_text(ser,text):
    #try:
    color = "white"
    color_bg = "black"
    position = (50, 50) 

    #    image = Image.open("input_image.jpg")
    #except FileNotFoundError:
    #    # Create a new image if the file isn't found for the example to work
    #    image = Image.new("RGB", (WIDTH, HEIGHT), color=color_bg)
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

    send_image(ser,image)


def send_aoostar_panel_graphics(ser, aoostar_screen_id=1, real_sensor_data=None, aoostar_data_path="C:/Program Files (x86)/AOOSTAR-X/_internal"):

    with open(aoostar_data_path + "/Monitor3.json", 'r', encoding='utf-8') as file:
            data = json.load(file)

    #for panel in data['mianban']: #mianban == panel

    try:
        image = Image.open(aoostar_data_path + "/sys_img/" + data['diy'][aoostar_screen_id - 1]['img']).convert('RGBA')
    except FileNotFoundError:
        print(f"Error loading {aoostar_data_path + '/sys_img/' + data['diy'][aoostar_screen_id - 1]['img']}")
        #exit(1)
        image = Image.new("RGBA", (960, 376), color = 'black')

    draw = ImageDraw.Draw(image)

    for sensor in data['diy'][aoostar_screen_id - 1]['sensor']:

        if real_sensor_data:
            try:
                sensor['value'] = real_sensor_data[sensor['label']]
            except:
                print(f"Error while:sensor['value'] = real_sensor_data[{sensor['label']}]")

        if isinstance(sensor['value'], float):
            sensor['value'] = round(sensor['value'])
        value = str(sensor['value']) + str(sensor['unit'])
        position = (sensor['x'], sensor['y']) 

        if sensor['mode'] == 1:

            try:
                font = ImageFont.truetype(aoostar_data_path + "/fonts/" + sensor['fontFamily'] + ".ttf", sensor['fontSize'])
            except IOError:
                print(f"Error loading {aoostar_data_path + '/fonts/' + sensor['fontFamily'] + '.ttf'}")
                #exit(1)
                font = None # Use default font if not available

            color = "white"

            anchor = "lm"
            if sensor['textAlign'] == "center": 
                anchor = "mm"
            elif sensor['textAlign'] == "right": 
                anchor = "rm"

            draw.text(position, value, fill=color, anchor=anchor, font=font)

        elif sensor['mode'] == 3:
            try:
                overlay = Image.open(aoostar_data_path + "/sys_img/" + sensor['pic']).convert('RGBA')
            except FileNotFoundError:
                print(f"Error loading {aoostar_data_path + '/sys_img/' + sensor['pic']}")
                #exit(1)
                overlay = Image.new("RGBA", (10, 10), color = 'black')

            width, height = overlay.size
            overlay = overlay.crop((
                0,
                0,
                int( width * float(sensor['value']) / float(sensor['maxValue']) ),
                height
                ))
            image.paste(overlay, position, mask=overlay)

    send_image(ser,image)
    #image.save(f"mianban{aoostar_screen_id}.png")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Basic controls for Aoostar GEM12 PRO MAX or WTR MAX screens",argument_default=argparse.SUPPRESS)

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--on", action="store_true",
                        dest="on",
                        help="Powers screen on")
    group.add_argument("--off", action="store_false",
                        dest="on",
                        help="Powers screen off")
    #group.set_defaults(on=True)

    subparsers = parser.add_subparsers(help='subcommands', dest='subcommand')
    parser_image = subparsers.add_parser("image", aliases=['i'], help="Sends image to be displayed")
    parser_image.add_argument("path", default="",
                        help="Image path")

    parser_text = subparsers.add_parser("text", aliases=['t'], help="Sends text to be displayed")
    parser_text.add_argument("content", default="",
                        help="Text to be displayed")

    parser_panel = subparsers.add_parser("panel", aliases=['p'], help="Sends Aoostar-X Panel to be displayed")
    parser_panel.add_argument("panel_id",
                              default="1",
                              help="Id of the panel to be displayed")

    parser_panel.add_argument("aoostar_internal_data_path",
                              default="C:/Program Files (x86)/AOOSTAR-X/_internal",
                              nargs="?",
                              help="Aoostar-X _internal path")

    parser_panel.add_argument("--hwinfo", action="store_true",
                              help="Get data from HWiNFO")

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

    if hasattr(args, 'on'):
        if args.on:
            lcd_on(ser)
        else:
            lcd_off(ser)

    match args.subcommand:
        case 'image':
            send_image_file(ser, args.path)
        case 'text':
            send_text(ser, args.content)
        case 'panel':
            if hasattr(args, 'on'):
                data = convertHWiNFODataToAoostarCompatible(getHWiNFOData())
            else:
                data = None
            send_aoostar_panel_graphics(ser, int(args.panel_id), data, args.aoostar_internal_data_path)

    ser.close()
