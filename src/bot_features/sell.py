
"""sell.py: Sells coin on kraken exchange based on users config file."""

import pandas as pd
from kraken_files.kraken_enums import *
from bot_features.base import Base
from pprint import pprint


class Sell(Base):
    def __init__(self, parameter_dict: dict) -> None:
        super().__init__(parameter_dict)
        self.asset_pairs_dict: dict = self.get_all_tradable_asset_pairs()[Dicts.RESULT]
        self.sell_order_placed: bool = False

    def __save_to_open_buy_orders(self, symbol_pair: str, df2: pd.DataFrame) -> None:
        """Write the DataFrame to an excel file."""
        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        df1 = pd.read_excel(filename, SheetNames.SAFETY_ORDERS)
        df3 = pd.read_excel(filename, SheetNames.OPEN_SELL_ORDERS)

        with pd.ExcelWriter(filename, engine=OPENPYXL, mode=FileMode.WRITE_TRUNCATE) as writer:
            df1.to_excel(writer, SheetNames.SAFETY_ORDERS,   index=False)
            df2.to_excel(writer, SheetNames.OPEN_BUY_ORDERS, index=False)
            df3.to_excel(writer, SheetNames.OPEN_SELL_ORDERS,index=False)
        return

    def __save_to_open_sell_orders(self, file_name: str, df3: pd.DataFrame) -> None:
        """Write the DataFrame to an excel file."""
        df1 = pd.read_excel(file_name, SheetNames.SAFETY_ORDERS)
        df2 = pd.read_excel(file_name, SheetNames.OPEN_BUY_ORDERS)

        with pd.ExcelWriter(file_name, engine=OPENPYXL, mode=FileMode.WRITE_TRUNCATE) as writer:
            df1.to_excel(writer, SheetNames.SAFETY_ORDERS, index=False)
            df2.to_excel(writer, SheetNames.OPEN_BUY_ORDERS,   index=False)
            df3.to_excel(writer, SheetNames.OPEN_SELL_ORDERS,   index=False)
        return

    def __get_quantity_owned(self, symbol: str) -> float:
        account_balance = self.get_account_balance()[Dicts.RESULT]
        for sym, qty in account_balance.items():
            if sym not in StableCoins.STABLE_COINS_LIST:
                if sym in symbol:
                    return float(qty)
        return 0.0

    def __cancel_sell_order(self, symbol_pair: str) -> None:
        """Open the sell_txids.xlsx file, cancel all sell orders by symbol name."""
        filename   = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        txids_list = pd.read_excel(filename, SheetNames.OPEN_SELL_ORDERS)[TXIDS].to_list()

        # on first sell order, there will be no txid inside of the sell_order sheet,
        # therefore, this for loop is skipped.
        for txid in txids_list:
            self.cancel_order(txid)
            df = pd.read_excel(filename, OSOColumns.TXIDS)
            df = df[ df[TXIDS] == txid]

            self.__save_to_open_sell_orders(filename, df)
        return

    def __get_required_price(self, symbol_pair: str) -> float:
        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        
        return float(pd.read_excel(filename, SheetNames.OPEN_BUY_ORDERS)[OBOColumns.REQ_PRICE][0])

    def __get_max_price_prec(self, symbol_pair: str) -> int:
        return self.get_max_price_precision(symbol_pair[:-4]) if StableCoins.ZUSD in symbol_pair else self.get_max_price_precision(symbol_pair[:-3])

    def __get_max_volume_prec(self, symbol_pair: str) -> int:
        return self.get_max_volume_precision(symbol_pair[:-4]) if StableCoins.ZUSD in symbol_pair else self.get_max_volume_precision(symbol_pair[:-3])

    def __place_sell_limit_order(self, symbol_pair: str) -> dict:
        required_price = self.round_decimals_down(self.__get_required_price(symbol_pair), self.__get_max_price_prec(symbol_pair)) 
        qty            = self.round_decimals_down(self.__get_quantity_owned(symbol_pair), self.__get_max_volume_prec(symbol_pair))
        return self.limit_order(Trade.SELL, qty, symbol_pair, required_price)

    def __update_open_buy_orders(self, symbol_pair: str) -> None:
        """If the first open_buy_order has been filled and the sell order has been placed successfully,
        we need to remove the first row in the open_buy_orders sheet as it is no longer open and needed 
        to place the next sell limit order."""

        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        df       = pd.read_excel(filename, SheetNames.OPEN_BUY_ORDERS)
        df.drop(0, inplace=True)
        self.__save_to_open_buy_orders(symbol_pair, df)
        return

    def __update_sell_order(self, symbol_pair: str, order_result: dict) -> None:
        """log the sell order in sell_orders/txids.xlsx."""
        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        
        if self.has_result(order_result):
            df                    = pd.read_excel(filename, SheetNames.OPEN_SELL_ORDERS)
            df.loc[len(df.index), OSOColumns.TXIDS] = order_result[Dicts.RESULT][Data.TXID][0]
            self.__save_to_open_sell_orders(filename, df)
        return

    def start(self, symbol_pair: str) -> None:
        """
        Triggered everytime a new buy limit order is placed.
            1. cancel all open sell orders for symbol_pair
            2. create a new sell limit order at the next 'Required price' column.
        """
        # cancel previous sell order (if it exists).
        self.__cancel_sell_order(symbol_pair)
        
        # place new sell order.
        sell_order_result = self.__place_sell_limit_order(symbol_pair)

        # update open_buy_orders sheet by removing filled buy orders.
        self.__update_open_buy_orders(symbol_pair)

        # update open_sell_orders sheet.
        self.__update_sell_order(symbol_pair, sell_order_result)

