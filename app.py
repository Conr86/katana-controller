#!/usr/bin/python3
# -*-python-*-

import sys
import os
import mido
import json
import RPi.GPIO as GPIO
from RPLCD import CharLCD
from katana import Katana
from range import Range

# which pins (number not broadcom id) the stomp-buttons are connected to    
stompButton = [7,12,16,15]
# pin that the bank button is connected to
bankButtonUp = 11
bankButtonDown = 13
# command line parameters
args = sys.argv
# location of preset file
preset_file = None

# patches in each bank (number of stomp buttons)
bankSize = 4
# current bank
currentBank = 1
# current patch
currentPatch = None
# whether bypass is enabled (ignore patch)
bypass = False
# all the banks, loaded from file
banks = {}
#presets = {}

class Bank:
    def __init__(self, name, id, presets):
        self.id = id
        self.name = name
        self.presets = presets # list or dictionary of presets
        
    def toJSON(self):
        data = {}
        data['name'] = self.name
        data['id'] = self.id
        data['presets'] = []
        for current_preset in self.presets:
           data['presets'].append(current_preset.toJSON())
        return data

class Preset:
    def __init__(self, id, name, parms):
        self.id = id
        self.name = name
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
    def load(self, katana):
        for current_parm in self.parms:
            addr_bytes = []
            data_bytes = []
            for hex in current_parm.split():
                addr_bytes.append(int(hex, 16))
            
            for hex in self.parms[current_parm].split():
                data_bytes.append( int(hex,16) )
            addr = tuple(addr_bytes)
            data = tuple(data_bytes)
            if addr[0] == 0xff:
                sleep(data[0] / 1000)
                continue
            katana.send_sysex_data(addr, data)
        
def print_lcd (line_1, line_2):
    lcd.clear()
    # First line
    lcd.cursor_pos = (0,0) 
    lcd.write_string(str(line_1))
    # Second Line
    lcd.cursor_pos = (1,0) 
    lcd.write_string(str(line_2))
    
# Capture and persist a new preset (overwrites existing)
def capture_preset( katana, bank, id ):
    name = input("Name: ")
    parms = {}
    for rec in rangeObj.get_coords():
        first = rec['baseAddr']
        last = rec['lastAddr']
        addr, data = katana.query_sysex_range(first, last)
        for a, d in zip( addr, data ):
            addr_hex = ' '.join( "%02x" % i for i in a)
            data_hex = ' '.join( "%02x" % i for i in d)
            parms[addr_hex] = data_hex

    banks[bank].presets[id] = Preset(id, name, parms)
    # Persist to disk
    save_presets()
    # Pulse for thing
    katana.signal()
                
def load_presets():
    with open(preset_file, 'r') as file:
        json_data = json.load(file)
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
   
   
'''
for preset in json_data:
    curr_id = int(preset)
    curr_name = json_data[preset]['name']
    curr_parms = {}
    
    # for every range thing (addr and data pair)
    for range in json_data[preset]['patch']:
        addr = str(range['addr'])
        data = str(range['data'])
        curr_parms[addr] = data
    presets[curr_id] = Preset(curr_id, curr_name, curr_parms)     
'''
# Rename existing data file and persist current
# live data to disk
def save_presets():
    try:
        with open(preset_file, 'w') as file:  
            json_data = {}
            for bank in banks:
                json_data[bank] = bank.toJSON()
                #for i in presets:
                #    json_data[i] = presets[i].toJSON()
            # save to file   
            json.dump(json_data, file, indent=4)
                    
    except OSError as e:
        print( "Error saving presets: " + e )
        # sys.exit( 1 )
    
def load_patch (id):
    banks[currentBank].presets[id].load(katana)
    currentPatch = banks[currentBank].presets[id]
    print("Loaded Patch {0}: {1}".format(id, currentPatch.name))
    print_lcd(banks[currentBank].name, currentPatch.name)
    return currentPatch

# Setup GPIO stuff
lcd = CharLCD(cols=16, rows=2, pin_rs=37, pin_e=35, pins_data=[33, 31, 29, 23])
for button in stompButton:
    GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
    GPIO.add_event_detect(button, GPIO.BOTH, bouncetime=500)
GPIO.setup(bankButtonUp, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(bankButtonDown, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(bankButtonUp, GPIO.BOTH, bouncetime=500)
GPIO.add_event_detect(bankButtonDown, GPIO.BOTH, bouncetime=500)
 
# Display loading        
print_lcd("Loading...","")

# Backend stuff
mido.set_backend('mido.backends.rtmidi')

# Load parameter metadata
scriptdir = os.environ.get('PYTHONPATH')
if scriptdir == None:
    scriptdir = os.path.dirname(os.path.abspath(__file__))
rangeObj = Range(scriptdir + '/parameters/ranges.json' )

# Amp interface
amp = args[1]
# Amp MIDI port 
try:
    amp_channel = int( args[2] ) - 1
except ValueError:
    print( "Arg2 must be numeric!\n" )
    sys.exit( 1 )
    
# Preset data
preset_file = args[3] #'presets.json'
load_presets()

# Setup amp
katana = Katana(amp, amp_channel, clear_input=True)
print_lcd("Katana Ready", "Select Patch")

try:
    while (1 < 2):
        #"""
        for buttonIndex, pin in enumerate(stompButton):
            if GPIO.event_detected(pin):
                patch_id = int(buttonIndex) + 1
                if patch_id in banks[currentBank].presets:
                    newPatch = banks[currentBank].presets[patch_id]
                    if (newPatch == currentPatch):
                        if bypass == True: 
                            bypass = False
                            print("Bypass disabled")
                        else:
                            bypass = True
                            print("Bypass enabled")
                    else:
                        bypass = False
                        currentPatch = load_patch(patch_id)                        
                else: 
                    # here we will 'load' an empty patch (actually just loading the panel)
                    katana.send_pc(4)
                    print("No Patch " + str(patch_id) + ". Loading panel.")
                    print_lcd(banks[currentBank].name, "New Patch")
                    currentPatch = None
        if GPIO.event_detected(bankButtonUp):
            currentBank += 1
            print_lcd(banks[currentBank].name, "Bank " + str(currentBank))
        if GPIO.event_detected(bankButtonDown):
            if(currentBank > 0):
                currentBank -= 1
                print_lcd(banks[currentBank].name, "Bank " + str(currentBank))
            
        """
        c = str(input("> "))
        #elif c == "list":
        #    for i in sorted(presets):
        #        print(str(i) + ": " + presets[i].name)
        if c == "save":
            # TODO
            i = int(input("Save As Patch Number: "))
            capture_preset(katana, i)
            print("Saved as " + presets[i].name)
        elif c == "up":
            currentBank += 1
            print_lcd(banks[currentBank].name, "Bank " + str(currentBank))
        elif c == "down":
            if(currentBank > 0):
                currentBank -= 1
                print_lcd(banks[currentBank].name, "Bank " + str(currentBank))
        elif c == "load":
            patch_id = int(input("Load Patch Number: "))
            if patch_id in banks[currentBank].presets:
                newPatch = banks[currentBank].presets[patch_id]
                if (newPatch == currentPatch):
                    if bypass == True: 
                        bypass = False
                        print("Bypass disabled")
                    else:
                        bypass = True
                        print("Bypass enabled")
                else:
                    bypass = False
                    load_patch(patch_id)
            else: 
                # here we will 'load' an empty patch (actually just loading the panel)
                katana.send_pc(4)
                print("No Patch " + str(patch_id) + ". Loading panel.")
                print_lcd(banks[currentBank].name, "New Patch")
        elif c == "channel":
            i = input("Load Channel (0-4): ")
            if i == "0":
                katana.send_pc(0)
                print("Loaded channel: " + str(i))
            elif i == "1":
                katana.send_pc(1)
                print("Loaded channel: " + str(i))
            elif i == "2":
                katana.send_pc(2)
                print("Loaded channel: " + str(i))
            elif i == "3":
                katana.send_pc(3)
                print("Loaded channel: " + str(i))
            elif i == "4":
                katana.send_pc(4)
                print("Loaded channel: " + str(i))
            else:
                print("Not valid")
        elif c == "clear":
            i = int(input("Clear Patch Number: "))
            presets.pop(i, None)
            save_presets()
            print ("Deleted preset " + str(i))
        #"""
            
finally:  
    GPIO.cleanup()
