import RPi.GPIO as GPIO

pins = [40, 38, 36, 37,32, 29, 24]

def pressed(pin):
    print('Pressed: ' + str(pin))
    

GPIO.setmode(GPIO.BOARD)
for pin in pins:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(pin, GPIO.BOTH, bouncetime=500, callback=pressed)

while(True):
    i = True