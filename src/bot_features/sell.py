
"""sell.py: Sells coin on kraken exchange based on users config file."""

import os
from pprint import pprint

import pandas as pd
from kraken_files.kraken_enums import *
from util.globals import G

from bot_features.base import Base

class Sell(Base):
    def __init__(self, parameter_dict: dict) -> None:
        super().__init__(parameter_dict)
        self.asset_pairs_dict: dict = self.get_all_tradable_asset_pairs()[Dicts.RESULT]

    def __create_directory(self) -> None:
        """Create a directory for the safety orders."""
        try:
            if not os.path.exists(EXCEL_FILES_DIRECTORY):
                os.mkdir(EXCEL_FILES_DIRECTORY)
        except Exception as e:
            G.log_file.print_and_log(e=e)
        return

    def __create_file(self, symbol_pair: str) -> None:
        """Create the sell order file if it doesn't exist."""
        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        if not os.path.exists(filename):
            self.__df_to_excel(filename, pd.DataFrame(data={TXIDS: []}) )
        return
    
    def __df_to_excel(self, file_name: str, df: pd.DataFrame) -> None:
        """Write the DataFrame to an excel file."""

        df1 = pd.read_excel(file_name, sheet_name=SheetNames.SOTABLE)
        df2 = pd.read_excel(file_name, sheet_name=SheetNames.OPEN_ORDERS)

        with pd.ExcelWriter(file_name, engine=OPENPYXL, mode=FileMode.WRITE_TRUNCATE) as writer:
            df1.to_excel(writer, sheet_name=SheetNames.SOTABLE,     index=False)
            df2.to_excel(writer, sheet_name=SheetNames.OPEN_ORDERS, index=False)
            df.to_excel(writer,  sheet_name=SheetNames.SELL_ORDERS, index=False)
        return

    def __get_quantity_owned(self, symbol: str) -> float:
        account_balance = self.get_account_balance()[Dicts.RESULT]
        for sym, qty in account_balance.items():
            if sym in symbol:
                return float(qty)
        return 0.0

    def __cancel_sell_order(self, symbol_pair: str) -> None:
        """Open the sell_txids.xlsx file, cancel all sell orders by symbol name."""
        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        txids_list = pd.read_excel(filename, sheet_name=SLColumns.TXIDS)[TXIDS].to_list()

        for txid in txids_list:
            self.cancel_order(txid)
            df = pd.read_excel(filename, sheet_name=SLColumns.TXIDS)
            df = df[ df[TXIDS] == txid]

            self.__df_to_excel(filename, df)
        return

    def get_required_price(self, symbol_pair: str) -> float:
        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        return float(pd.read_excel(filename)[SOColumns.REQ_PRICE][0])

    def __get_max_price_prec(self, symbol_pair: str) -> int:
        return self.get_max_price_precision(symbol_pair[:-4]) if "ZUSD" in symbol_pair else self.get_max_price_precision(symbol_pair[:-3])

    def __get_max_volume_prec(self, symbol_pair: str) -> int:
        return self.get_max_volume_precision(symbol_pair[:-4]) if "ZUSD" in symbol_pair else self.get_max_volume_precision(symbol_pair[:-3])

    def __place_sell_limit_order(self, symbol_pair: str) -> dict:
        required_price = self.round_decimals_down(self.get_required_price(symbol_pair), self.__get_max_price_prec(symbol_pair))
        qty            = self.round_decimals_down(self.__get_quantity_owned(symbol_pair), self.__get_max_volume_prec(symbol_pair))
        return self.limit_order(Trade.SELL, qty, symbol_pair, required_price)

    def __update_sell_order(self, symbol_pair: str, order_result: dict) -> None:
        """log the sell order in sell_orders/txids.xlsx."""
        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        pprint(order_result) # {'error': ['EOrder:Insufficient funds']}
        df                    = pd.read_excel(filename)
        df.loc[len(df.index)] = order_result[Dicts.RESULT][Data.TXID]

        self.__df_to_excel(filename, df)
        return

    def start(self, symbol_pair: str) -> None:
        """
        Triggered everytime a new buy limit order is placed.
            1. cancel all open sell orders for symbol_pair
            2. create a new sell limit order at the next 'Required price' column.
        """
        # self.__create_directory()
        # self.__create_file(symbol_pair)
        self.__cancel_sell_order(symbol_pair)
        order_result = self.__place_sell_limit_order(symbol_pair)
        self.__update_sell_order(symbol_pair, order_result)
