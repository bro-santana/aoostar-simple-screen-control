class AoostarDataModel:
    def __init__(self):
        self.DATE_m_d_h_m_2 : str = ""
        self.cpu_temperature : float = 0.0
        self.cpu_percent : float = 0.0
        self.memory_usage : float = 0.0
        self.memory_Temperature = 0 #original data has a capital T
        self.net_ip_address : str = ""
        self.gpu_core : float = 0.0
        self.gpu_temperature : float = 0.0
        self.net_upload_speed : float = 0.0
        self.net_upload_speed_unit : str = ""
        self.net_download_speed : float = 0.0
        self.net_download_speed_unit : str = ""
        self.motherboard_temperature : float = 0.0
        self.storage_ssd = [
          {
            "temperature": 0.0,
            "used": 0.0
          },
          {
            "temperature": 0.0,
            "used": 0
          },
          {
            "temperature": 0.0,
            "used": 0.0
          },
          {
            "temperature": 0.0,
            "used": 0.0
          },
          {
            "temperature": 0.0,
            "used": 0.0
          }
        ]
        self.storage_hdd = [
          {
            "temperature": 0.0,
            "used": 0.0
          },
          {
            "temperature": 0.0,
            "used": 0.0
          },
          {
            "temperature": 0.0,
            "used": 0.0
          },
          {
            "temperature": 0.0,
            "used": 0.0
          },
          {
            "temperature": 0.0,
            "used": 0.0
          },
          {
            "temperature": 0.0,
            "used": 0.0
          }
        ]

    @staticmethod
    def _split_aoostar_compound_key(key):
        delimiters = ['[', ']', '\'', '"']
        for delimiter in delimiters:
            key = key.replace(delimiter, ' ')
        return key.split()

    def get(self,key:str):
        match key:
            case "DATE_m_d_h_m_2":
                return self.DATE_m_d_h_m_2
            case "cpu_temperature":
                return self.cpu_temperature
            case "cpu_percent":
                return self.cpu_percent
            case "memory_usage":
                return self.memory_usage
            case "memory_Temperature":
                return self.memory_Temperature
            case "net_ip_address":
                return self.net_ip_address
            case "gpu_core":
                return self.gpu_core
            case "gpu_temperature":
                return self.gpu_temperature
            case "net_upload_speed":
                return str(round(self.net_upload_speed,1)) + " " + self.net_upload_speed_unit
            case "net_download_speed":
                return str(round(self.net_download_speed,1)) + " " + self.net_download_speed_unit
            case "motherboard_temperature":
                return self.motherboard_temperature
            case str(partial_key) if partial_key.startswith("storage_ssd"):
                split_key = self._split_aoostar_compound_key(key)
                return self.storage_ssd[int(split_key[1])][split_key[2]]
            case str(partial_key) if partial_key.startswith("storage_hdd"):
                split_key = self._split_aoostar_compound_key(key)
                return self.storage_hdd[int(split_key[1])][split_key[2]]
