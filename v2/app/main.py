import modules.tg.main as tg

import configparser
import os


__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))


def main():
    config = configparser.ConfigParser()
    config.read(os.path.join(__location__, "settings.ini"))
    
    tg.run_bot_and_block_thread(config["tg"]["token"])
    
    
if __name__ == "__main__":
    main()