import json

from datetime import datetime
from requests import get

from hwinfo_sharedmem import HWiNFOReader

def getHWiNFOData():
    try:
        with HWiNFOReader() as hwinfo:
            print("Connected to HWiNFO Shared Memory...")
            
            snapshot = hwinfo.read_data()
            
            if "error" in snapshot:
                print(f"Error: {snapshot['error']}")
            else:
                print(f"HWiNFO Version: {snapshot['version']}")
                print(f"Total Sensors: {len(snapshot['sensors'])}")
                print(f"Total Readings: {len(snapshot['readings'])}")

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
        print(f"Connection Failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def convertHWiNFODataToAoostarCompatible(snapshot):

    with open('aoostar_data_model.json','r',encoding='utf-8') as f:
        aoostar_data = json.load(f)

    ssd_count_smart = 0
    ssd_count_drive = 0

    #Find better way to adjust this non sourced data
    aoostar_data["DATE_m_d_h_m_2"] = datetime.now().strftime("%b %d/%H/%M") #Time differs from snapshot
    try:
        aoostar_data["net_ip_address"] = get('https://api.ipify.org').content.decode('utf8')
    except:
        print("Error getting external ip")

    for r in snapshot['readings']:

        if r['label_orig'] == "CPU Core" :
            aoostar_data["cpu_temperature"] = r['value']

        elif r['label_orig'] == "Total CPU Utility" :
            aoostar_data["cpu_percent"] = r['value']

        elif r['label_orig'] == "Physical Memory Load" :
            aoostar_data["memory_usage"] = r['value']

        elif r['label_orig'] == "SPD Hub Temperature" :
            aoostar_data["memory_Temperature"] = max(aoostar_data["memory_Temperature"],r['value'])

        elif r['label_orig'] == "GPU Core Load" :
            aoostar_data["gpu_core"] = max(aoostar_data["gpu_core"],r['value']) #any gpu?

        elif r['label_orig'] == "GPU Temperature" :
            aoostar_data["gpu_temperature"] = max(aoostar_data["gpu_temperature"],r['value']) #any gpu?

        elif r['label_orig'] == "Current UP rate" :
            aoostar_data["net_upload_speed"] = str(round(r['value'])) + " " + str(r['unit'])

        elif r['label_orig'] == "Current DL rate" :
            aoostar_data["net_download_speed"] = str(round(r['value'])) + " " + str(r['unit'])

        elif "Temperature " in r['label_orig'] :
            aoostar_data["motherboard_temperature"] = max(aoostar_data["motherboard_temperature"], r['value'])

        elif "S.M.A.R.T.: " in r['sensor_name'] and r['label_orig'] == "Drive Temperature" :
            aoostar_data["storage_ssd"][ssd_count_smart]["temperature"] = r['value']
            ssd_count_smart += 1 #can the order from Drive and Smart be different?

        elif "Drive: " in r['sensor_name'] and r['label_orig'] == "Total Activity" :
            aoostar_data["storage_ssd"][ssd_count_drive]["used"] = r['value']
            ssd_count_drive += 1 #can the order from Drive and Smart be different?

    return aoostar_data

if __name__ == "__main__":
    snapshot = getHWiNFOData()
    aoostar_data = convertHWiNFODataToAoostarCompatible(snapshot)

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=4)

    with open('aoostar_compatible_data.json', 'w', encoding='utf-8') as f:
        json.dump(aoostar_data, f, ensure_ascii=False, indent=4)
