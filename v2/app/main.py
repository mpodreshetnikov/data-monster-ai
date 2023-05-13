import logging
import configparser
import os

import modules.tg.main as tg


__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))


def main():
    config = configparser.ConfigParser()
    config.read(os.path.join(__location__, "settings.ini"))
    
    is_debug = config.getboolean("debug", "is_debug", fallback=False)
    
    log_path = config.get("common", "log_path", fallback="logs")
    __configure_logger__(log_path, verbose=is_debug)
    
    tg_bot_token = config.get("tg", "bot_token")
    tg_users_whitelist = config.get("tg", "whitelist").split(",")
    tg.run_bot_and_block_thread(tg_bot_token, tg_users_whitelist)
    
    
def __configure_logger__(log_path: str, log_filename: str = 'log.txt', verbose: bool = False):
    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    root_logger = logging.getLogger()

    file_handler = logging.FileHandler("{0}/{1}".format(log_path, log_filename))
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    if verbose:
        root_logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        root_logger.addHandler(console_handler)
        
        
if __name__ == "__main__":
    main()