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
from presets import * # PresetsHandler, Bank, Preset, Range

# current bank
currentBank = 1

# all the banks, loaded from file
banks = {}

# Saving a preset, waiting for user to press the button to tell it where to save to
capturing = False

# Load config file
config = Config('config.toml')

# Using the GPIO pin numbers (BOARD) instead of broadcom ids (BCM)
# If you import RPLCD, it sets the mode to BOARD as well, so we'll stick with it.
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

for pin in config.leds['pins']:
    GPIO.setup(pin, GPIO.OUT)

# Setup LCD screen, using value in config file
if (config.lcd['use_i2c'] == True):
    i2c_bus = config.lcd['i2c_bus']
    i2c_addr = config.lcd['i2c_addr']
    lcd = i2c_lcd_driver.lcd(i2c_bus, int(i2c_addr, 16))
    lcd.backlight(0)
else:
    lcd = CharLCD(cols = config.lcd['cols'], rows=config.lcd['rows'], pin_rs=config.lcd['pin_rs'], pin_e=config.lcd['pin_e'], pins_data=config.lcd['pins_data'])
    

def print_lcd (line_1, line_2 = '', line_3 = '', line_4=''):
    lcd.clear()
    # First line
    lcd.cursor_pos = (0,0) 
    lcd.write_string(str(line_1))
    # Second Line
    lcd.cursor_pos = (1,0) 
    lcd.write_string(str(line_2))
    # Third
    lcd.cursor_pos = (2,0) 
    lcd.write_string(str(line_3))
    # Fourth
    lcd.cursor_pos = (3,0) 
    lcd.write_string(str(line_4))
    
def rename_bank(bank):
    name = str (input("New bank name: "))
    banks[bank].name = name
    print_lcd("Renamed bank {0} to {1}".format(bank, name))
    
# Capture and persist a new preset (overwrites existing)
def capture_preset(bank, id):

    # Display message
    print_lcd("Saving in bank {0}".format(bank),"Preset {0}".format(id))
    
    # Construct the preset
    name = str(input("Name: "))
    parms = {}
    for rec in rangeObj.get_coords():
        first = rec['baseAddr']
        last = rec['lastAddr']
        addr, data = katana.query_sysex_range(first, last)
        for a, d in zip( addr, data ):
            addr_hex = ' '.join( "%02x" % i for i in a)
            data_hex = ' '.join( "%02x" % i for i in d)
            parms[addr_hex] = data_hex

    if bank not in banks:
        # Create new bank
        banks[bank] = Bank("New Bank", presets = {})
        
    # Add to bank
    banks[bank].presets[id] = Preset(name, parms)
    
    # Persist to disk
    PresetsHandler.save_presets(banks, config.files['preset_file'])
    
    # Do thing on the amp, so we know it's done something
    katana.signal()
    
def buttonPressed (buttonIndex):
    patch_id = int(config.buttons['stomp_buttons'].index(buttonIndex)) + 1
    global capturing
        
    for pin in config.leds['pins']:
        GPIO.output(pin, GPIO.LOW)
    GPIO.output(config.leds['pins'][patch_id - 1], GPIO.HIGH)
    
    if (capturing == True):
        capture_preset(currentBank, patch_id)
        capturing = False
        return
        
    # If currentBank is System Bank (0)
    if (currentBank == 0):
        loadChannel(patch_id - 1)
        
    # If currentBank is a used bank (1-9 with patches)
    elif currentBank in banks:
        # Check if there is a patch for the button pressed
        if patch_id in banks[currentBank].presets: # Bank exists and preset exists
            # Get the new patch from the banks
            newPatch = banks[currentBank].presets[patch_id]
            # Load the new patch
            load_patch(patch_id)
        else: # Bank exists, but empty preset
            # Here we will 'load' an empty patch (actually just loading the panel)
            katana.send_pc(4)
            print_lcd("Bank {0}".format(currentBank), banks[currentBank].name, "New Patch")
            
    else: # Empty Bank
        # Here we will 'load' an empty patch (actually just loading the panel)
        katana.send_pc(4)
        print_lcd("Bank {0}".format(currentBank), "Empty Bank", "New Patch")
     
def load_patch (id):
    # Load the patch to the Katana amp
    katana.load_patch(banks[currentBank].presets[id].parms)
    # Set (local) currentPatch to be the new patch
    currentPatch = banks[currentBank].presets[id]
    # Update screen with new patch name
    print_lcd("Bank {0}".format(currentBank),  banks[currentBank].name, currentPatch.name)
    #print("Loaded Patch {0}: {1}".format(id, currentPatch.name))
    # This will set global currentPatch to be the current patch
      
def updateBankScreen():
    # Prints the current bank name and number
    # Prints different text if the bank is 0 or a new bank
    #print("Bank " + str(currentBank))
    if (currentBank == 0):
        print_lcd("Bank 0", "System Bank")
    else:
        if currentBank in banks:
            print_lcd("Bank " + str(currentBank), banks[currentBank].name)
        else:
            print_lcd("Bank " + str(currentBank), "Untitled Bank")
            
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

def loadChannel (channel):
    katana.send_pc(int(channel))
    #print("Loading channel {0}".format(channel))
    if int(channel) == 4:
        print_lcd("Bank 0", "System Bank", "Panel")
    else:
        print_lcd("Bank 0", "System Bank", "Channel {0}".format(int(channel) + 1))
    
# Setup GPIO buttons
for button in config.buttons['stomp_buttons']:
    GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
    GPIO.add_event_detect(button, GPIO.RISING, bouncetime=500, callback=buttonPressed)
# Setup events for bank up and down buttons
GPIO.setup(config.buttons['bank_button_up'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(config.buttons['bank_button_down'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(config.buttons['bank_button_up'], GPIO.BOTH, bouncetime=500, callback=bank_change)
GPIO.add_event_detect(config.buttons['bank_button_down'], GPIO.BOTH, bouncetime=500, callback=bank_change)

# Display loading screen, will probably only display if clear_true is true
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
            
try:
    while (True):
        c = str(input("> "))
        if c == "list":
            for i in banks:
                print (banks[i].name)
                for j in sorted(banks[i].presets):
                    print("  {0}: {1}".format(j, banks[i].presets[j].name))
        elif c == "save":
            capturing = True
            print("Capturing...")
            print_lcd("Capturing...", "")
        elif c == "save all":
            PresetsHandler.save_presets(banks, config.files['preset_file'])
            print("Saved all presets to disk")
        elif c == "up":
            currentBank += 1
            print_lcd(banks[currentBank].name, "Bank " + str(currentBank))
        elif c == "down":
            if(currentBank > 0):
                currentBank -= 1
                print_lcd(banks[currentBank].name, "Bank " + str(currentBank))
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