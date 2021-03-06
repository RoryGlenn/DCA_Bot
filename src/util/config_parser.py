"""config_parser.py - scans for config.txt file and applies users settings."""

import json
import os
import sys

from util.globals                        import G
from bot_features.low_level.kraken_enums import *


class ConfigParser():
    def assign_enum_values() -> dict:
        """Assign values to the enums"""
        reg_list = ['ETC',  'ETH',  'LTC',  'MLN',  'REP',  'XBT',  'XDG',  'XLM',  'XMR',  'XRP',  'ZEC' ]
        
        if os.path.exists(CONFIG_JSON):
            with open(CONFIG_JSON) as file:
                try:
                    config = json.load(file)[ConfigKeys.CONFIG]
                
                    for symbol in config[ConfigKeys.BUY_SET]:
                        if symbol in reg_list:
                            Buy_.SET.add("X" + symbol)
                        else:
                            Buy_.SET.add(symbol)
                    
                    Buy_.SET = sorted(Buy_.SET)
                    
                    # DCA
                    DCA_.TARGET_PROFIT_PERCENT          = float(config[ConfigKeys.DCA_TARGET_PROFIT_PERCENT])
                    DCA_.SAFETY_ORDER_VOLUME_SCALE      = float(config[ConfigKeys.DCA_SAFETY_ORDER_VOLUME_SCALE])
                    DCA_.SAFETY_ORDERS_MAX              = int  (config[ConfigKeys.DCA_SAFETY_ORDERS_MAX])
                    DCA_.SAFETY_ORDERS_ACTIVE_MAX       = int  (config[ConfigKeys.DCA_SAFETY_ORDERS_ACTIVE_MAX])
                    DCA_.SAFETY_ORDER_STEP_SCALE        = float(config[ConfigKeys.DCA_SAFETY_ORDER_STEP_SCALE])
                    DCA_.SAFETY_ORDER_PRICE_DEVIATION   = float(config[ConfigKeys.DCA_SAFETY_ORDER_PRICE_DEVIATION])
                except Exception as e:
                    G.log.print_and_log(e=e, error_type=type(e).__name__, filename=__file__, tb_lineno=e.__traceback__.tb_lineno)
                    sys.exit()
        else:
            G.log.print_and_log("Could not find config.json file")
            sys.exit()
            
    def get_config():
        if os.path.exists(CONFIG_JSON):
            with open(CONFIG_JSON) as file:
                try:
                    return json.load(file)[ConfigKeys.CONFIG]
                except Exception as e:
                    G.log.print_and_log(e=e, error_type=type(e).__name__, filename=__file__, tb_lineno=e.__traceback__.tb_lineno)
                    sys.exit()
        else:
            G.log.print_and_log("Could not find config.json file")
            sys.exit()            