import mido
import time

amp = 'KATANA:KATANA MIDI 1 20:0'
channel = 1

pc = mido.Message('program_change')
pc.channel = channel