import json
from hwinfo_sharedmem import HWiNFOReader

if __name__ == "__main__":
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

                with open('data.json', 'w', encoding='utf-8') as f:
                    json.dump(snapshot, f, ensure_ascii=False, indent=4)

    except FileNotFoundError as e:
        print(f"Connection Failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
