# !/usr/bin/env python

"""main.py: Entry point for the Kraken bot"""

__author__     = "Rory M. Glenn"
__copyright__  = "Copyright 2021, Kraken-Bot"
__credits__    = ["Girzan", "Boods"]
__license__    = "MIT"
__version__    = "1.0"
__maintainer__ = "Rory Glenn"
__email__      = "glennrory@gmail.com"
__status__     = "Production"

import os
import sys
from datetime import datetime
from threading import Thread

from bot_features.buy import Buy
from bot_features.distribution import Distribution
from bot_features.sell import Sell
from kraken_files.kraken_enums import Buy_, Distribution_, Misc, Sell_, Threads
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


# OL6YIS-SSHEY-CDLGMA

# Safety Order No.	Deviation, %	Quantity	Price $	      Average Price $	Required price	Required Change %
# 0	                0	            10	        0.369615	  0.369615	        0.371463075	    0.5
# 1	                1.3	            10	        0.364810005	  0.367212503	    0.369048565	    1.148510092
# 2	                3.328	        25	        0.357314213	  0.362263358	    0.364074674	    1.856888741
# 3	                6.49168	        62.5	    0.345620777	  0.353942067	    0.355711778	    2.836847502
# 4	                11.4270208	    156.25	    0.327379017	  0.340660542	    0.342363845	    4.376872165
# 5	                19.12615245	    390.625	    0.298921872	  0.319791207	    0.321390163	    6.990970449
# 6	                31.13679782	    976.5625	0.254528725	  0.287159966	    0.288595766	    11.80441468
# 7	                49.8734046	    2441.40625	0.185275416	  0.236217691	    0.237398779	    21.95603691
