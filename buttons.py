import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)

class ButtonHandler:
    bypass = False
    currentBank = 1

    def __init__(self, stomp_buttons, bank_button_up, bank_button_down):
        self.stomp_buttons = stomp_buttons
        self.bank_button_down = bank_button_down
        self.bank_button_up = bank_button_up
        self.setup()
        
    def setup(self):
        # Setup GPIO buttons
        for button in self.stomp_buttons:
            GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
            GPIO.add_event_detect(button, GPIO.BOTH, bouncetime=500)
        # Setup events for bank up and down buttons
        GPIO.setup(self.bank_button_up, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.bank_button_down, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.bank_button_up, GPIO.BOTH, bouncetime=500)
        GPIO.add_event_detect(self.bank_button_down, GPIO.BOTH, bouncetime=500)