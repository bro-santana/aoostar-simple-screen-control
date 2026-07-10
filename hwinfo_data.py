import json
import time

from datetime import datetime
from requests import get

from aoostar_data_model import AoostarDataModel
from hwinfo_sharedmem import HWiNFOReader

# External IP cache so repeated conversions don't hit the network every time
_EXTERNAL_IP_TTL_SECONDS = 300
_external_ip_cache = {"value": "", "fetched_at": 0.0}

def getExternalIP() -> str:
    now = time.monotonic()
    if _external_ip_cache["value"] and now - _external_ip_cache["fetched_at"] < _EXTERNAL_IP_TTL_SECONDS:
        return _external_ip_cache["value"]
    try:
        _external_ip_cache["value"] = get('https://api.ipify.org', timeout=5).content.decode('utf8')
        _external_ip_cache["fetched_at"] = now
    except Exception:
        print("Error getting external ip")
    return _external_ip_cache["value"]

# Avoid repeating the "HWiNFO not running" message on every refresh
_hwinfo_error_printed = {"done": False}

def getHWiNFOData() -> dict:
    try:
        with HWiNFOReader() as hwinfo:
            snapshot = hwinfo.read_data()

            if "error" in snapshot:
                print(f"Error: {snapshot['error']}")

                #print("-" * 60)
                #print(f"{'SENSOR':<30} | {'LABEL':<20} | {'VALUE':<10} | {'UNIT'}")
                #print("-" * 60)
                #
                ## Print a few examples (CPU/GPU temps usually interesting)
                #for r in snapshot['readings']:
                #    # Simple filter to keep output clean, remove if you want to see everything
                #    if r['type'] in ["Temp", "Power", "Usage"]: 
                #        val_str = f"{r['value']:.1f}"
                #        print(f"{r['sensor_name']:<30} | {r['label']:<20} | {val_str:<10} | {r['unit']}")

            return snapshot

    except FileNotFoundError as e:
        if not _hwinfo_error_printed["done"]:
            print(f"Connection Failed: {e}")
            _hwinfo_error_printed["done"] = True
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def convertHWiNFODataToAoostarCompatible(snapshot) -> AoostarDataModel:

    aoostar_data = AoostarDataModel()

    ssd_count_smart = 0
    ssd_count_drive = 0

    #Find better way to adjust this non sourced data
    aoostar_data.DATE_m_d_h_m_2 = datetime.now().strftime("%b %d %H:%M") #Time differs from snapshot
    aoostar_data.net_ip_address = getExternalIP()

    for r in snapshot['readings']:

        if r['label_orig'] == "CPU Core" :
            aoostar_data.cpu_temperature = r['value']

        elif r['label_orig'] == "Total CPU Utility" :
            aoostar_data.cpu_percent = r['value']

        elif r['label_orig'] == "Physical Memory Load" :
            aoostar_data.memory_usage = r['value']

        elif r['label_orig'] == "SPD Hub Temperature" :
            aoostar_data.memory_Temperature = max(aoostar_data.memory_Temperature,r['value'])

        elif r['label_orig'] == "GPU Core Load" :
            aoostar_data.gpu_core = max(aoostar_data.gpu_core,r['value']) #any gpu?

        elif r['label_orig'] == "GPU Temperature" :
            aoostar_data.gpu_temperature = max(aoostar_data.gpu_temperature,r['value']) #any gpu?

        elif r['label_orig'] == "Current UP rate" :
            aoostar_data.net_upload_speed = r['value']
            aoostar_data.net_upload_speed_unit = r['unit']

        elif r['label_orig'] == "Current DL rate" :
            aoostar_data.net_download_speed = r['value']
            aoostar_data.net_download_speed_unit = r['unit']

        elif "Temperature " in r['label_orig'] :
            aoostar_data.motherboard_temperature = max(aoostar_data.motherboard_temperature, r['value'])

        elif "S.M.A.R.T.: " in r['sensor_name'] and r['label_orig'] == "Drive Temperature" :
            aoostar_data.storage_ssd[ssd_count_smart]["temperature"] = r['value']
            ssd_count_smart += 1 #can the order from Drive and Smart be different?

        elif "Drive: " in r['sensor_name'] and r['label_orig'] == "Total Activity" :
            aoostar_data.storage_ssd[ssd_count_drive]["used"] = r['value']
            ssd_count_drive += 1 #can the order from Drive and Smart be different?

    return aoostar_data

if __name__ == "__main__":
    snapshot = getHWiNFOData()
    aoostar_data = convertHWiNFODataToAoostarCompatible(snapshot)

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=4)

    with open('aoostar_compatible_data.json', 'w', encoding='utf-8') as f:
        json.dump(aoostar_data.__dict__, f, ensure_ascii=False, indent=4)
