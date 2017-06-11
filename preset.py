import json

'''
This module contains any classes involving presets, e.g. bank, preset and the PresetsHandler

The structure for classes is like this:

banks
    Bank 1
        - name
        - id
        - presets
            - Preset 1
                - name
                - id
                - Ranges
                    - addr
                    - data
                    - addr
                    - data
            - Preset 2
                - name
                - id
                - Ranges
                    - addr
                    - data
                    - addr
                    - data
    Bank 2
        - name
        - ...

'''
class Bank:
    def __init__(self, name, id, presets):
        # Unique bank id
        self.id = id
        # Bank name
        self.name = name 
        # List or dictionary of presets
        self.presets = presets 
        
    def toJSON(self):
        # Returns data ready to be dumped as json file
        data = {}
        data['name'] = self.name
        data['id'] = self.id
        data['presets'] = []
        for current_preset in self.presets:
           data['presets'].append(current_preset.toJSON())
        return data        
        
class Preset:
    def __init__(self, id, name, parms):
        # Preset id (probably between 1 and 4)
        self.id = id
        # Name of preset
        self.name = name
        # The actual patch (address and data)
        self.parms = parms
        
    def toJSON(self):
        item = {}
        item['name'] = self.name
        item['patch'] = []
        for current_parm in self.parms:
            item['patch'].append({
                'addr': current_parm,
                'data': self.parms[current_parm]
            })
        return item

class Range:
    def __init__( self, parmfile ):
        with open(parmfile) as json_file:
            self.recs = json.load( json_file )

    def get_coords( self ):
        return self.recs    
    
class PresetsHandler:         
    # This class handles all the reading and writing to the preset file
    
    # Load all banks and presets from preset file
    def load_presets(preset_file):
        with open(preset_file, 'r') as file:
            json_data = json.load(file)
        banks = {}
        for bank in json_data:
            # get current bank id
            bank_id = int(bank)
            # get current bank's name
            bank_name = json_data[bank]['name']
            # create empty container for all the presets in the bank
            bank_presets = {}
            # add all the presets to the bank
            for preset in json_data[bank]['presets']:
                preset_id = int(preset)
                preset_name = json_data[bank]['presets'][preset]['name']
                preset_parms = {}
                # for every range thing (addr and data pair)
                for range in json_data[bank]['presets'][preset]['patch']:
                    addr = str(range['addr'])
                    data = str(range['data'])
                    preset_parms[addr] = data
                # add current preset to current bank
                bank_presets[preset_id] = Preset(preset_id, preset_name, preset_parms)
            # add bank to bank database thing
            banks[bank_id] = Bank(bank_name, bank_id, bank_presets)
        return banks
        
    # Save all live data to preset file
    def save_presets(banks, preset_file):
        try:
            # Open preset file
            with open(preset_file, 'w') as file:  
                json_data = {}
            for bank in banks:
                json_data[bank] = bank.toJSON()
            # Save to file  
            json.dump(json_data, file, indent=4) 
        except OSError as e:
            print( "Error saving presets: " + e )