import modules.tg.main as tg

import configparser
import os


__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))


def main():
    config = configparser.ConfigParser()
    config.read(os.path.join(__location__, "settings.ini"))
    
    tg_bot_token = config["tg"]["bot_token"]
    tg_users_whitelist = config["tg"]["whitelist"].split(",")
    tg.run_bot_and_block_thread(tg_bot_token, tg_users_whitelist)
    
    
if __name__ == "__main__":
    main()