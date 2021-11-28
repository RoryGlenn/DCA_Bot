"""config_parser.py - scans for config.txt file and applies users settings."""

import sys

from bot_features.kraken_enums import *
from util.globals              import G


class ConfigParser():
    def __get_parameter_list(self) -> list:
        return [
            # kraken
            ConfigKeys.KRAKEN_API_KEY, 
            ConfigKeys.KRAKEN_SECRET_KEY,
            
            # dca
            ConfigKeys.DCA_TARGET_PROFIT_PERCENT,
            ConfigKeys.DCA_BASE_ORDER_SIZE,
            ConfigKeys.DCA_SAFETY_ORDERS_MAX,
            ConfigKeys.DCA_SAFETY_ORDERS_ACTIVE_MAX,
            ConfigKeys.DCA_SAFETY_ORDER_SIZE,
            ConfigKeys.DCA_SAFETY_ORDER_STEP_SCALE,
            ConfigKeys.DCA_SAFETY_ORDER_VOLUME_SCALE,
            ConfigKeys.DCA_SAFETY_ORDER_PRICE_DEVIATION]

    def parse_config_file(self) -> None:
        """
        Parses FileMode.CONFIG_FILE. 
        Strips out an unnecessary characters and store key/value pairs in dictionary.
        Args can be rearranged to the users desire.

        """
        parameter_dict = dict()
        removed_set    = set()
        parameter_list = self.__get_parameter_list()
        replace_list   = ["\n", "\t", " ", '"']

        try:
            with open(FileMode.CONFIG_FILE, mode=FileMode.READ_ONLY) as file:
                for line in file.readlines():
                    for char in replace_list:
                        line = line.replace(char, "")

                    # get the index where "=" occurres first
                    first_equal_sign_index = line.find("=")

                    # Remove the first occurrence of "=" with affecting anything else
                    line = line[:first_equal_sign_index] + line[first_equal_sign_index+1:]

                    for param in parameter_list:
                        if param in line and param not in removed_set:
                            line = line.replace(param, "")
                            parameter_dict[param] = line
                            removed_set.add(param)
                            break
        except Exception as e:
            G.log_file.print_and_log(e=e, error_type=type(e).__name__, filename=__file__, tb_lineno=e.__traceback__.tb_lineno)
            sys.exit()
        return parameter_dict

    def assign_enum_values(self) -> None:
        """Assign the values to our enums"""
        cfg_dict = ConfigParser().parse_config_file()

        # DCA
        DCA_.TARGET_PROFIT_PERCENT          = float(cfg_dict[ConfigKeys.DCA_TARGET_PROFIT_PERCENT]       )
        DCA_.SAFETY_ORDER_VOLUME_SCALE      = float(cfg_dict[ConfigKeys.DCA_SAFETY_ORDER_VOLUME_SCALE]   )
        DCA_.SAFETY_ORDERS_MAX              = int  (cfg_dict[ConfigKeys.DCA_SAFETY_ORDERS_MAX]           )
        DCA_.SAFETY_ORDERS_ACTIVE_MAX       = int  (cfg_dict[ConfigKeys.DCA_SAFETY_ORDERS_ACTIVE_MAX]    )
        DCA_.SAFETY_ORDER_STEP_SCALE        = float(cfg_dict[ConfigKeys.DCA_SAFETY_ORDER_STEP_SCALE]     )
        DCA_.SAFETY_ORDER_PRICE_DEVIATION   = float(cfg_dict[ConfigKeys.DCA_SAFETY_ORDER_PRICE_DEVIATION])
        return
