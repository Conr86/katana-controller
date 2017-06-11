#!/usr/bin/python3
# -*-python-*-

import sys
import os
import mido
import RPi.GPIO as GPIO
from RPLCD import CharLCD
from katana import Katana
from config import Config
from preset import * # PresetsHandler, Bank, Preset, Range

# current bank
currentBank = 1
# current patch
currentPatch = None

# whether bypass is enabled (ignore patch)
bypass = False
# all the banks, loaded from file
banks = {}

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
    save_presets(config.files['preset_file'], banks)
    # Pulse for thing
    katana.signal()

def load_patch (id):
    # Load the patch to the Katana amp
    katana.load_patch(banks[currentBank].presets[id].parms)
    # Set (local) currentPatch to be the new patch
    currentPatch = banks[currentBank].presets[id]
    # Update screen with new patch name
    print_lcd(banks[currentBank].name, currentPatch.name)
    print("Loaded Patch {0}: {1}".format(id, currentPatch.name))
    # This will set global currentPatch to be the current patch
    return currentPatch
    
# Load config file
config = Config('config.toml')

# Setup LCD screen, using value in config file
lcd = CharLCD(cols = config.lcd['cols'], rows=config.lcd['rows'], pin_rs=config.lcd['pin_rs'], pin_e=config.lcd['pin_e'], pins_data=config.lcd['pins_data'])
    
# Display loading screen     
print_lcd("Loading...","")

# Setup GPIO buttons
for button in config.buttons['stomp_buttons']:
    GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
    GPIO.add_event_detect(button, GPIO.BOTH, bouncetime=500)
# Setup events for bank up and down buttons
GPIO.setup(config.buttons['bank_button_up'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(config.buttons['bank_button_down'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(config.buttons['bank_button_up'], GPIO.BOTH, bouncetime=500)
GPIO.add_event_detect(config.buttons['bank_button_down'], GPIO.BOTH, bouncetime=500)

# Backend stuff
mido.set_backend(config.katana['backend'])

# Load parameter metadata
rangeObj = Range(config.files['ranges_file'])

# Load presets
banks = PresetsHandler.load_presets(config.files['preset_file'])

# Setup amp
katana = Katana(config.katana['amp'], config.katana['channel'], config.katana['clear_input'])
print_lcd("Katana Ready", "Select Patch")

try:
    while (1 < 2):
        #"""
        for buttonIndex, pin in enumerate(config.buttons['stomp_buttons']):
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
        if GPIO.event_detected(config.buttons['bank_button_up']):
            currentBank += 1
            print_lcd(banks[currentBank].name, "Bank " + str(currentBank))
        if GPIO.event_detected(config.buttons['bank_button_down']):
            if(currentBank > 0):
                currentBank -= 1
                print_lcd(banks[currentBank].name, "Bank " + str(currentBank))
            
        """
        c = str(input("> "))
        if c == "list":
            for i in banks:
                print (banks[i].name)
                for j in sorted(banks[i].presets):
                    print("  {0}: {1}".format(j, banks[i].presets[j].name))
        elif c == "save":
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
        elif c == "channel":
            i = int(input("Load Channel (0-4): "))
            if i <= 4:
                katana.send_pc(i)
                print("Loaded channel: " + str(i))
            else:
                print("Not valid")
        elif c == "clear":
            i = int(input("Clear Patch Number: "))
            banks[currentBank].presets.pop(i, None)
            save_presets()
            print ("Deleted preset " + str(i))
        #"""
            
finally:  
    GPIO.cleanup()