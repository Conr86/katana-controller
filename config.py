import toml

class Config:
    # Load a config file
    def __init__(self, file):
        with open(file) as conffile:
            config = toml.loads(conffile.read())
        # Sections of the config file
        self.general = config['general']
        self.katana = config['katana']
        self.files = config['files']
        self.lcd = config['lcd']
        self.buttons = config['buttons']