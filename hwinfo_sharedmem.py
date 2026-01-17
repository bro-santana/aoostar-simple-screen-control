import ctypes
from ctypes import wintypes
import time

# ==============================================================================
# CONSTANTS & CONFIGURATION
# ==============================================================================

HWiNFO_SENSORS_MAP_FILE_NAME2 = "Global\\HWiNFO_SENS_SM2"
HWiNFO_SENSORS_MAP_FILE_NAME2_REMOTE =  "Global\\HWiNFO_SENS_SM2_REMOTE_"
HWiNFO_SENSORS_SM2_MUTEX      = "Global\\HWiNFO_SM2_MUTEX"

HWiNFO_SENSORS_STRING_LEN2 = 128
HWiNFO_UNIT_STRING_LEN     = 16

# Windows API Constants
FILE_MAP_READ = 0x0004

# Sensor Reading Types (Enum)
SENSOR_TYPE_NONE    = 0
SENSOR_TYPE_TEMP    = 1
SENSOR_TYPE_VOLT    = 2
SENSOR_TYPE_FAN     = 3
SENSOR_TYPE_CURRENT = 4
SENSOR_TYPE_POWER   = 5
SENSOR_TYPE_CLOCK   = 6
SENSOR_TYPE_USAGE   = 7
SENSOR_TYPE_OTHER   = 8

# Reading type to string map for display
READING_TYPE_NAMES = {
    0: "None", 1: "Temp", 2: "Volt", 3: "Fan", 
    4: "Current", 5: "Power", 6: "Clock", 7: "Usage", 8: "Other"
}

def c_char_array_to_string(data):
    return data.decode('mbcs', errors='replace')

def c_ubyte_array_to_string(data):
    return bytearray(data).split(b'\0', 1)[0].decode('utf-8', errors='replace')

# ==============================================================================
# CTYPES STRUCTURE DEFINITIONS
# ==============================================================================

class HWiNFO_SENSORS_READING_ELEMENT(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("tReading",      ctypes.c_int),          # SENSOR_READING_TYPE (Enum is int)
        ("dwSensorIndex", ctypes.c_uint32),
        ("dwReadingID",   ctypes.c_uint32),
        ("szLabelOrig",   ctypes.c_char * HWiNFO_SENSORS_STRING_LEN2),
        ("szLabelUser",   ctypes.c_char * HWiNFO_SENSORS_STRING_LEN2),
        ("szUnit",        ctypes.c_char * HWiNFO_UNIT_STRING_LEN),
        ("Value",         ctypes.c_double),
        ("ValueMin",      ctypes.c_double),
        ("ValueMax",      ctypes.c_double),
        ("ValueAvg",      ctypes.c_double),
        ("utfLabelUser",  ctypes.c_ubyte * HWiNFO_SENSORS_STRING_LEN2),
        ("utfUnit",       ctypes.c_ubyte * HWiNFO_UNIT_STRING_LEN),
    ]

    def get_label(self, use_utf8=False):
        if use_utf8:
            return c_ubyte_array_to_string(self.utfLabelUser)
        return c_char_array_to_string(self.szLabelUser)

    def get_label_orig(self):
        return c_char_array_to_string(self.szLabelOrig)

    def get_unit(self, use_utf8=False):
        if use_utf8:
            return c_ubyte_array_to_string(self.utfUnit)
        return c_char_array_to_string(self.szUnit)

    def get_python_dict(self):
        return {
            "tReading":      self.tReading,
            "dwSensorIndex": self.dwSensorIndex,
            "dwReadingID":   self.dwReadingID,
            "szLabelOrig":   c_char_array_to_string(self.szLabelOrig),
            "szLabelUser":   c_char_array_to_string(self.szLabelUser),
            "szUnit":        c_char_array_to_string(self.szUnit),
            "Value":         self.Value,
            "ValueMin":      self.ValueMin,
            "ValueMax":      self.ValueMax,
            "ValueAvg":      self.ValueAvg,
            "utfLabelUser":  c_ubyte_array_to_string(self.utfLabelUser),
            "utfUnit":       c_ubyte_array_to_string(self.utfUnit),
        }

class HWiNFO_SENSORS_SENSOR_ELEMENT(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("dwSensorID",        ctypes.c_uint32),
        ("dwSensorInst",      ctypes.c_uint32),
        ("szSensorNameOrig",  ctypes.c_char * HWiNFO_SENSORS_STRING_LEN2),
        ("szSensorNameUser",  ctypes.c_char * HWiNFO_SENSORS_STRING_LEN2),
        ("utfSensorNameUser", ctypes.c_ubyte * HWiNFO_SENSORS_STRING_LEN2),
    ]

    def get_name(self, use_utf8=False):
        if use_utf8:
            return c_ubyte_array_to_string(self.utfSensorNameUser)
        return c_char_array_to_string(self.szSensorNameUser)

    def get_name_orig(self):
        return c_char_array_to_string(self.szSensorNameOrig)

    def get_python_dict(self):
        return {
            "dwSensorID":        self.dwSensorID,
            "dwSensorInst":      self.dwSensorInst,
            "szSensorNameOrig":  c_char_array_to_string(self.szSensorNameOrig),
            "szSensorNameUser":  c_char_array_to_string(self.szSensorNameUser),
            "utfSensorNameUser": c_ubyte_array_to_string(self.utfSensorNameUser),
        }

class HWiNFO_SENSORS_SHARED_MEM2(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("dwSignature",             ctypes.c_uint32),
        ("dwVersion",               ctypes.c_uint32),
        ("dwRevision",              ctypes.c_uint32),
        ("poll_time",               ctypes.c_int64), # __time64_t
        ("dwOffsetOfSensorSection", ctypes.c_uint32),
        ("dwSizeOfSensorElement",   ctypes.c_uint32),
        ("dwNumSensorElements",     ctypes.c_uint32),
        ("dwOffsetOfReadingSection", ctypes.c_uint32),
        ("dwSizeOfReadingElement",  ctypes.c_uint32),
        ("dwNumReadingElements",    ctypes.c_uint32),
        ("dwPollingPeriod",         ctypes.c_uint32),
    ]

# ==============================================================================
# MAIN ACCESS CLASS
# ==============================================================================

class HWiNFOReader:
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self.h_map_file = None
        self.p_shared_mem = None
        self.base_address = 0

        self.kernel32.OpenFileMappingW.restype = wintypes.HANDLE
        self.kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]

        self.kernel32.MapViewOfFile.restype = wintypes.LPVOID
        self.kernel32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, 
                                          wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]

        self.kernel32.UnmapViewOfFile.argtypes = [ctypes.wintypes.LPCVOID]
        self.kernel32.UnmapViewOfFile.restype = ctypes.wintypes.BOOL

        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    def __enter__(self):
        # Open the File Mapping
        self.h_map_file = self.kernel32.OpenFileMappingW(
            FILE_MAP_READ, 
            False, 
            HWiNFO_SENSORS_MAP_FILE_NAME2
        )

        if not self.h_map_file:
            raise FileNotFoundError(
                "Could not open HWiNFO Shared Memory. "
                "Ensure HWiNFO is running and 'Shared Memory Support' is enabled in settings."
            )

        # Map the view of the file
        self.base_address = self.kernel32.MapViewOfFile(
            self.h_map_file,
            FILE_MAP_READ,
            0, 0, 0
        )

        if not self.base_address:
            self.kernel32.CloseHandle(self.h_map_file)
            raise MemoryError("Could not map view of file.")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.base_address:
            self.kernel32.UnmapViewOfFile(self.base_address)
        if self.h_map_file:
            self.kernel32.CloseHandle(self.h_map_file)

    def read_data(self):
        # Cast the base address to the Header Struct
        header = HWiNFO_SENSORS_SHARED_MEM2.from_address(self.base_address)
        
        # Verify Signature "HWiS"
        # H = 0x48, W = 0x57, i = 0x69, S = 0x53
        # Little Endian: 0x53695748
        if header.dwSignature != 0x53695748:
             # Depending on endianness and packing, sometimes checking bytes is safer:
             sig_bytes = header.dwSignature.to_bytes(4, byteorder='little')
             if sig_bytes != b'HWiS':
                 return {"error": "Invalid HWiNFO Signature"} #OR DEAD

        #is_utf8_capable = (header.dwVersion >= 2)
        is_utf8_capable = False
        
        data = {
            "version": header.dwVersion,
            "revision": header.dwRevision,
            "poll_time": header.poll_time,
            #"sensors_raw": {},
            #"readings_raw": [],
            "sensors": {},
            "readings": []
        }

        # Calculate start address for Sensors
        sensor_section_addr = self.base_address + header.dwOffsetOfSensorSection
        
        for i in range(header.dwNumSensorElements):
            # Calculate address of current sensor
            current_sensor_addr = sensor_section_addr + (i * header.dwSizeOfSensorElement)
            sensor = HWiNFO_SENSORS_SENSOR_ELEMENT.from_address(current_sensor_addr)

            # Store sensor info map (Index -> Name)
            data["sensors"][i] = {
                "id": sensor.dwSensorID,
                "inst": sensor.dwSensorInst,
                "name_orig": sensor.get_name_orig(),
                "name": sensor.get_name(is_utf8_capable)
            }

            #data["sensors_raw"][i] = sensor.get_python_dict()

        # Calculate start address for Readings
        reading_section_addr = self.base_address + header.dwOffsetOfReadingSection

        for i in range(header.dwNumReadingElements):
            current_reading_addr = reading_section_addr + (i * header.dwSizeOfReadingElement)
            reading = HWiNFO_SENSORS_READING_ELEMENT.from_address(current_reading_addr)
            
            sensor_index = reading.dwSensorIndex
            sensor_name = data["sensors"].get(sensor_index, {}).get("name", "Unknown Sensor")

            reading_data = {
                "sensor_index": sensor_index,
                "sensor_name": sensor_name,
                "label_orig": reading.get_label_orig(),
                "label": reading.get_label(is_utf8_capable),
                "type": READING_TYPE_NAMES.get(reading.tReading, "Unknown"),
                "value": reading.Value,
                "unit": reading.get_unit(is_utf8_capable),
                "value_min": reading.ValueMin,
                "value_max": reading.ValueMax,
                "value_avg": reading.ValueAvg
            }
            data["readings"].append(reading_data)

            #data["readings_raw"].append(reading.get_python_dict())

        return data

# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================
#
#if __name__ == "__main__":
#    try:
#        with HWiNFOReader() as hwinfo:
#            print("Connected to HWiNFO Shared Memory...")
#            
#            snapshot = hwinfo.read_data()
#            
#            if "error" in snapshot:
#                print(f"Error: {snapshot['error']}")
#            else:
#                print(f"HWiNFO Version: {snapshot['version']}")
#                print(f"Total Sensors: {len(snapshot['sensors'])}")
#                print(f"Total Readings: {len(snapshot['readings'])}")
#                print("-" * 60)
#                print(f"{'SENSOR':<30} | {'LABEL':<20} | {'VALUE':<10} | {'UNIT'}")
#                print("-" * 60)
#                
#                # Print a few examples (CPU/GPU temps usually interesting)
#                for r in snapshot['readings']:
#                    # Simple filter to keep output clean, remove if you want to see everything
#                    if r['type'] in ["Temp", "Power", "Usage"]: 
#                        val_str = f"{r['value']:.1f}"
#                        print(f"{r['sensor_name']:<30} | {r['label']:<20} | {val_str:<10} | {r['unit']}")
#
#    except FileNotFoundError as e:
#        print(f"Connection Failed: {e}")
#    except Exception as e:
#        print(f"An unexpected error occurred: {e}")
