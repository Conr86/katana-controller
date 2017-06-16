#!/usr/bin/python3
# -*-python-*-

import sys
import os
import mido
import RPi.GPIO as GPIO
#from RPLCD import CharLCD
import i2c_lcd_driver
from katana import Katana
from config import Config
from buttons import ButtonHandler
from presets import * # PresetsHandler, Bank, Preset, Range

# current bank
currentBank = 1

# all the banks, loaded from file
banks = {}

# Load config file
config = Config('config.toml')

# Setup LCD screen, using value in config file
if (config.lcd['use_i2c'] == True):
    i2c_bus = config.lcd['i2c_bus']
    i2c_addr = config.lcd['i2c_addr']
    lcd = i2c_lcd_driver.lcd(i2c_bus, int(i2c_addr, 16))
    lcd.backlight(0)
else:
    lcd = CharLCD(cols = config.lcd['cols'], rows=config.lcd['rows'], pin_rs=config.lcd['pin_rs'], pin_e=config.lcd['pin_e'], pins_data=config.lcd['pins_data'])
    

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
    
def buttonPressed (buttonIndex):
    patch_id = int(config.buttons['stomp_buttons'].index(buttonIndex)) + 1
   
    # If currentBank is System Bank (0)
    if (currentBank == 0):
        loadChannel(patch_id - 1)
    # If currentBank is a used bank (1-9 with patchs)
    elif currentBank in banks:
        # Check if there is a patch for the button pressed
        if patch_id in banks[currentBank].presets:
            # Get the new patch from the banks
            newPatch = banks[currentBank].presets[patch_id]
            # Load the new patch
            load_patch(patch_id)
        else: 
            # here we will 'load' an empty patch (actually just loading the panel)
            katana.send_pc(4)
            print("No Patch " + str(patch_id) + ". Loading panel.")
            print_lcd(banks[currentBank].name, "New Patch")
    # If currentBank is an empty bank (1-9 without patches)
    else:
        # here we will 'load' an empty patch (actually just loading the panel)
        katana.send_pc(4)
        print("No Patch " + str(patch_id) + ". Loading panel.")
        print_lcd("Empty Bank", "New Patch")
     
def load_patch (id):
    # Load the patch to the Katana amp
    katana.load_patch(banks[currentBank].presets[id].parms)
    # Set (local) currentPatch to be the new patch
    currentPatch = banks[currentBank].presets[id]
    # Update screen with new patch name
    print_lcd(banks[currentBank].name, currentPatch.name)
    print("Loaded Patch {0}: {1}".format(id, currentPatch.name))
    # This will set global currentPatch to be the current patch
      
def updateBankScreen():
    # Prints the current bank name and number
    # Prints different text if the bank is 0 or a new bank
    print("Bank " + str(currentBank))
    if (currentBank == 0):
        print_lcd("System Bank", "Bank 0")
    else:
        if currentBank in banks:
            print_lcd(banks[currentBank].name, "Bank " + str(currentBank))
        else:
            print_lcd("Untitled Bank", "Bank " + str(currentBank))
            
def bank_change(button):
    global currentBank
    if button == config.buttons['bank_button_up']:
        currentBank += 1
        if (currentBank > config.general['number_of_banks']):
            currentBank = 0
        updateBankScreen()
    else:
        currentBank -= 1
        if (currentBank < 0):
            currentBank = config.general['number_of_banks']
        updateBankScreen()
   

# Setup button handler
#buttonHandler = ButtonHandler(config.buttons['stomp_buttons'], config.buttons['bank_button_up'], config.buttons['bank_button_down'])

# Setup GPIO buttons
for button in config.buttons['stomp_buttons']:
    GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
    GPIO.add_event_detect(button, GPIO.RISING, bouncetime=500, callback=buttonPressed)
# Setup events for bank up and down buttons
GPIO.setup(config.buttons['bank_button_up'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(config.buttons['bank_button_down'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(config.buttons['bank_button_up'], GPIO.BOTH, bouncetime=500, callback=bank_change)
GPIO.add_event_detect(config.buttons['bank_button_down'], GPIO.BOTH, bouncetime=500, callback=bank_change)

# Display loading screen     
print_lcd("Loading...","")

# Backend stuff
mido.set_backend(config.katana['backend'])

# Load parameter metadata
rangeObj = Range(config.files['ranges_file'])

# Load presets
banks = PresetsHandler.load_presets(config.files['preset_file'])

# Setup amp
katana = Katana(config.katana['amp'], config.katana['channel'], config.katana['clear_input'])
print_lcd("Katana Ready", "Select Patch")

def loadChannel (channel):
    katana.send_pc(int(channel))
    print("Loading channel {0}".format(channel))
    print_lcd("System Bank", "Channel {0}".format(channel))
            
try:
    while (1 < 2):
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
            
finally:  
    GPIO.cleanup()