# !/usr/bin/env python

"""main.py: Entry point for the DCA bot"""

__author__     = "Rory M. Glenn"
__copyright__  = "Copyright 2021, DCA-Bot"
__license__    = "MIT"
__version__    = "1.0"
__maintainer__ = "Rory Glenn"
__email__      = "glennrory@gmail.com"
__status__     = "Production"

import os
import sys
from datetime import datetime

from bot_features.buy import Buy
from kraken_files.kraken_enums import *
from util.config_parser import ConfigParser
from util.globals import G


class General:
    def clear_terminal() -> None:
        os.system(Misc.CLEAR)

    def get_current_time() -> None:
        """ 
        Gets the current time in hours, minutes, seconds

        """
        return datetime.now().strftime("%H:%M:%S")

    def windows_sync_time() -> None:
        """
        Sync windows time in case we get disconnected from Kraken API

        """

        G.log_file.print_and_log("Sync windows time on startup")

        if sys.platform != "win32":
            print_and_log(
                f"Kraken Rake bot is not build for {str(sys.platform)}. Please run on a Windows machine")
            return

        try:
            G.log_file.print_and_log("w32tm /resync")

            if os.system("w32tm /resync") != 0:
                G.log_file.print_and_log(
                    "Windows time sync failed, configuring settings")
                os.system(
                    "w32tm /config /manualpeerlist:time.nist.gov /syncfromflags:manual /reliable:yes /update")
                os.system("Net stop w32time")
                os.system("Net start w32time")
            else:
                G.log_file.print_and_log("Windows time sync successful.")
        except Exception as e:
            G.log_file.print_and_log(
                message="Failed to sync windows time.", e=e)

    def init_threads() -> None:
        """ 
        Initialize threads for buying, selling, tipping and distribution. 

        """

        cfg_dict    = ConfigParser().parse_config_file()
        ConfigParser().assign_enum_values()
        
        buy = Buy(cfg_dict)
        buy.buy_loop()
        return

def main() -> None:
    General.clear_terminal()
    G.log_file.directory_create()
    G.log_file.file_create()
    General.windows_sync_time()
    General.init_threads()
    G.log_file.print_and_log("Exiting main thread")


###########################################
### MAIN ###
###########################################
if __name__ == "__main__":
    main()
    