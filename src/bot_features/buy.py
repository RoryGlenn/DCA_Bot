
"""buy.py: Buys coin on kraken exchange based on users config file.

1. Have a list of coins that you want to buy.
2. Pull data from trading view based on 3c settings.
3. Make decision on whether to buy or not.
4. After base order is filled, create sell limit order at 0.5% higher
5. every time a safety order is filled, cancel current sell limit order and create a new sell limit order
"""

import datetime
import glob
import os
from pprint import pprint

import pandas as pd
from kraken_files.kraken_enums import *
from util.globals import G

from bot_features.base import Base
from bot_features.dca import DCA
from bot_features.sell import Sell
from bot_features.tradingview import TradingView


class Buy(Base):
    def __init__(self, parameter_dict: dict) -> None:
        super().__init__(parameter_dict)
        
        self.account_balance:         dict  = {}
        self.kraken_assets_dict:      dict  = {}
        self.trade_history:           dict  = {}
        self.bid_price:               float = 0.0
        self.quantity_to_buy:         float = 0.0
        self.symbol_pair:             str   = ""
        self.is_buy:                  bool  = False
        self.dca:                     DCA   = None
        self.sell:                    Sell  = Sell(parameter_dict)        
        return

    def __init_loop_variables(self) -> None:
        """Initialize variables for the buy_loop."""
        self.kraken_assets_dict = self.get_asset_info()[Dicts.RESULT]
        self.account_balance    = self.get_parsed_account_balance()
        self.asset_pairs_dict   = self.get_all_tradable_asset_pairs()[Dicts.RESULT]
        self.__create_order_txids_directory()
        self.__create_txids_file()
        return

    def __get_buy_time(self) -> str:
        """Returns the next time to buy as specified in the config file."""
        return ( datetime.timedelta(minutes=Buy_.TIME_MINUTES) + datetime.datetime.now() ).strftime("%H:%M:%S")

    def __create_order_txids_directory(self) -> None:
        """Create the order_txids directory."""
        if not os.path.exists(ORDER_TXIDS_DIRECTORY):
            os.mkdir(ORDER_TXIDS_DIRECTORY)
        return

    def __create_txids_file(self) -> None:
        """Create the txids.xlsx file."""
        if not os.path.exists(TXIDS_FILE):
            d = {TXIDS: []}
            df = pd.DataFrame(data=d)
            with pd.ExcelWriter(TXIDS_FILE, engine=ENGINE, mode=FileMode.WRITE_TRUNCATE) as writer:
                df.to_excel(writer, sheet_name=TXID_SHEET, index=False)
        return

    def __get_recommendation(self, symbol_pair: str) -> bool:
        """Get the recommendation from trading view."""
        ta = TradingView()
        return ta.is_buy(symbol_pair)

    def __set_pre_buy_variables(self, symbol: str) -> None:
        """Sets the buy variables for each symbol."""
        self.symbol_pair = self.get_tradable_asset_pair(symbol)
        self.bid_price   = self.get_bid_price(self.symbol_pair)
        alt_name         = self.get_alt_name(symbol)
        self.is_buy      = self.__get_recommendation(alt_name+StableCoins.USD)
        # is the coin a buy and do we already own the coin?
        return

    def __df_to_excel(self, file_name: str, sheet_name: str, df: pd.DataFrame) -> None:
        """Write the DataFrame to an excel file."""
        with pd.ExcelWriter(file_name, engine=ENGINE, mode=FileMode.WRITE_TRUNCATE) as writer:
            df.to_excel(writer, index=False)
        return

    def save_order_txid(self, buy_result: dict) -> None:
        """
        Once a limit order is placed successfully, update the TXIDS_FILE
        by appending the new txid to the end of the file.
        Note: This function is called only in __place_limit_orders().
        """
        df = pd.read_excel(TXIDS_FILE)
        df.loc[len(df.index)] = buy_result[Dicts.RESULT][Data.TXID]
        self.__df_to_excel(TXIDS_FILE, TXID_SHEET, df)
        return

    def __get_open_orders_on_symbol_pair(self) -> str:
        """Returns the number of open orders for self.symbol_pair."""
        count = 0
        if self.has_result(self.open_orders):
            for _, dictionary in self.open_orders[Dicts.RESULT][Dicts.OPEN].items():
                if dictionary[Dicts.DESCR][Data.PAIR] == self.symbol_pair:
                    count += 1
        return count

    def __set_post_buy_variables(self, symbol: str) -> None:
        """Sets variables in order to make an buy order."""
        self.wait(timeout=Nap.LONG)
        order_min                = self.get_order_min(symbol)
        self.pair_decimals       = self.get_pair_decimals(self.symbol_pair)
        self.open_orders         = self.get_open_orders()
        self.dca                 = DCA(self.symbol_pair, order_min, self.bid_price)
        self.dca.account_balance = self.get_parsed_account_balance()
        return

    def __place_limit_orders(self, symbol: str) -> None:
        """Place the safety orders that were set inside of the DCA class.
        If the limit order was entered successfully, update the excel sheet by removing the order we just placed.
        """
        num_open_orders    = self.__get_open_orders_on_symbol_pair()
        num_orders_to_make = abs(num_open_orders-DCA_.SAFETY_ORDERS_ACTIVE_MAX)

        # if the max active orders are already put in, and are still active, there is nothing left to do.
        if num_open_orders >= DCA_.SAFETY_ORDERS_ACTIVE_MAX:
            # Max safety orders are already active.
            return

        for _, safety_order_dict in self.dca.safety_orders.items():
            for price, quantity in safety_order_dict.items():
                price_max_prec   = self.get_pair_decimals(self.symbol_pair)
                rounded_price    = self.round_decimals_down(price, price_max_prec) # WHY DOESN'T get_pair_decimals WORK HERE???????
                rounded_quantity = self.round_decimals_down(quantity, self.get_max_volume_precision(symbol))
                req_profit_price = self.round_decimals_down(self.sell.get_required_price(self.symbol_pair), price_max_prec)
                cc_buy_result    = self.limit_order_conditional_close(Trade.BUY, rounded_quantity, self.symbol_pair, rounded_price, req_profit_price, rounded_quantity)

                if self.has_result(cc_buy_result):
                    G.log_file.print_and_log(message=f"buy_loop: limit order placed {self.symbol_pair} {cc_buy_result}", money=True)
                    
                    # keep track of the open order txid
                    self.save_order_txid(cc_buy_result)

                    """once the limit order was entered successfully, delete it from the excel sheet"""
                    self.dca.update_safety_orders()
                    num_orders_to_make -= 1
                else:
                    G.log_file.print_and_log(message=f"buy_loop: {cc_buy_result}", money=True)

            if num_orders_to_make <= 0:
                break
        return

    def __update_filled_limit_orders(self) -> None:
        """
        Updates the AVERAGE_PRICES_FILE if a buy limit order has been filled.
        Accomplishes this by checking to see if the txid exists in the trade history list.

        1. Read all txids from txids.xlsx file into DataFrame.
        2. For every txid of in the dataframe, check if the associated order has been filled.
        3. If the limit buy order has been filled, update the AVERAGE_PRICES_FILE with the new average and new quantity.
        
        Note: Function is called only once inside of the buy loop.
        
        """
        filled_trades_order_txids = dict()
        self.trade_history        = self.get_trades_history()
        df                        = pd.read_excel(TXIDS_FILE)
        
        for trade_txid, dictionary in self.trade_history[Dicts.RESULT][Data.TRADES].items():
            filled_trades_order_txids[dictionary[Data.ORDER_TXID]] = trade_txid

        for order_txid in df[TXIDS].to_list():
            if order_txid in filled_trades_order_txids:
                # if the txid is in the trade history, the order was filled.

                # remove txid from txids.xlsx.
                df = df[ df[TXIDS] == order_txid ]

                # rewrite file
                self.__df_to_excel(TXIDS_FILE, TXID_SHEET, df)
        return

    def __update_completed_safety_order_files(self) -> None:
        """For every file that exists in the safety_orders directory, check if it contains any more safety orders.
        If it is empty and there are no open orders on that symbol, delete the file.
        
        If the txid for the open orders does not exist inside of txid.xlsx, should we add to it???????????????????????????????

        """
        open_orders:             dict = self.get_open_orders()[Dicts.RESULT][Dicts.OPEN]
        open_order_symbol_pairs: set  = {d[Dicts.DESCR][Data.PAIR] for (_, d) in open_orders.items()}

        for file in glob.iglob(SAFETY_ORDER_DIRECTORY+"/"+"\*.xlsx"):
            df          = pd.read_excel(file)
            symbol_pair = file.split("\\")[-1].replace(".xlsx", "") # get the file name without the extention (symbol_pair)

            if len(df.index) == 0 and symbol_pair not in open_order_symbol_pairs:
                """there are no more safety orders left to place, so delete the file."""
                os.remove(file)
        return


##################################################################################################################################
### BUY_LOOP
##################################################################################################################################

    def buy_loop(self) -> None:
        """The main function for buying coin."""
        self.cancel_all_orders()
        self.__init_loop_variables()

        while True:
            try:
                # if our orders were filled change the average price file to the new price and qty
                self.__update_filled_limit_orders()
                self.__update_completed_safety_order_files()

                self.wait(message=f"buy_loop: Waiting till {self.__get_buy_time()} to buy", timeout=Buy_.TIME_MINUTES*60)

                for symbol in Buy_.LIST:
                    self.wait(message=f"buy_loop: checking asset {symbol}", timeout=Nap.LONG)
                    self.__set_pre_buy_variables(symbol)
                    
                    if not self.is_buy: continue

                    self.__set_post_buy_variables(symbol)
                    self.__place_limit_orders(symbol)
            except Exception as e:
                G.log_file.print_and_log(message="buy_loop:", e=e)
        return
