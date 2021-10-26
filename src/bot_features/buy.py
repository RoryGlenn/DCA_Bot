
"""buy.py: Buys coin on kraken exchange based on users config file.

1. Have a list of coins that you want to buy.
2. Pull data from trading view based on 3c settings.
3. Make decision on whether to buy or not.
4. After base order is filled, create sell limit order at % higher
5. every time a safety order is filled, cancel current sell limit order and create a new sell limit order
"""

############## Buy list in DCA bot should be decided from the HULL moving average in trading view.!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

import datetime
import os
import pandas as pd
import glob

from pprint                    import pprint

from kraken_files.kraken_enums import *
from util.globals              import G
from bot_features.base         import Base
from bot_features.dca          import DCA
from bot_features.sell         import Sell
from bot_features.tradingview  import TradingView


class Buy(Base):
    def __init__(self, parameter_dict: dict) -> None:
        super().__init__(parameter_dict)
        
        self.account_balance:         dict  = { }
        self.kraken_assets_dict:      dict  = { }
        self.trade_history:           dict  = { }
        self.bid_price:               float = 0.0
        self.quantity_to_buy:         float = 0.0
        self.symbol_pair:             str   = ""
        self.is_buy:                  bool  = False
        self.dca:                     DCA   = None
        self.sell:                    Sell  = Sell(parameter_dict)
        self.ta:                      TradingView = TradingView()
        return

    def __init_loop_variables(self) -> None:
        """Initialize variables for the buy_loop."""
        self.kraken_assets_dict = self.get_asset_info()[Dicts.RESULT]
        self.account_balance    = self.get_parsed_account_balance()
        self.asset_pairs_dict   = self.get_all_tradable_asset_pairs()[Dicts.RESULT]
        self.__create_excel_directory()
        self.update_buy_list()
        return

    def __get_buy_time(self) -> str:
        """Returns the next time to buy as specified in the config file."""
        return ( datetime.timedelta(minutes=Buy_.TIME_MINUTES) + datetime.datetime.now() ).strftime("%H:%M:%S")

    def __create_excel_directory(self) -> None:
        """Create the excel_files directory."""
        if not os.path.exists(EXCEL_FILES_DIRECTORY):
            os.mkdir(EXCEL_FILES_DIRECTORY)
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
        return

    def save_open_buy_order_txid(self, buy_result: dict, symbol_pair: str, required_price: float) -> None:
        """
        Once a limit order is placed successfully, update the order orders file
        by appending the new txid to the end of the file.
        Note: This function is called only in __place_limit_orders().
        """
        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"

        if os.path.exists(filename):
            df_sa = pd.read_excel(filename, SheetNames.SAFETY_ORDERS)
            df_oo = pd.read_excel(filename, SheetNames.OPEN_BUY_ORDERS)
            df_so = pd.read_excel(filename, SheetNames.OPEN_SELL_ORDERS)

            df_oo.loc[len(df_oo),   OBOColumns.TXIDS]     = buy_result[Dicts.RESULT][Data.TXID][0]
            df_oo.loc[len(df_oo)-1, OBOColumns.REQ_PRICE] = required_price

            with pd.ExcelWriter(filename, engine=OPENPYXL, mode=FileMode.WRITE_TRUNCATE) as writer:
                df_sa.to_excel(writer, SheetNames.SAFETY_ORDERS,    index=False)
                df_oo.to_excel(writer, SheetNames.OPEN_BUY_ORDERS,  index=False)
                df_so.to_excel(writer, SheetNames.OPEN_SELL_ORDERS, index=False)
        return

    def __get_open_orders_on_symbol_pair(self, symbol: str) -> str:
        """Returns the number of open orders for self.symbol_pair."""
        count = 0
        alt_symbol_pair = self.get_alt_name(symbol) + StableCoins.USD

        if self.has_result(self.open_orders):
            for _, dictionary in self.open_orders[Dicts.RESULT][Dicts.OPEN].items():
                if dictionary[Dicts.DESCR][Data.PAIR] == alt_symbol_pair:
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

    def __get_required_price(self):
        filename = EXCEL_FILES_DIRECTORY + "/" + self.symbol_pair + ".xlsx"
        df       = pd.read_excel(filename, SheetNames.SAFETY_ORDERS)
        return float(df[SOColumns.REQ_PRICE].to_list()[0])

    def __place_limit_orders(self, symbol: str) -> None:
        """Place the safety orders that were set inside of the DCA class.
        If the limit order was entered successfully, update the excel sheet by removing the order we just placed.
        """
        try:
            num_open_orders    = self.__get_open_orders_on_symbol_pair(symbol)
            num_orders_to_make = abs(num_open_orders-DCA_.SAFETY_ORDERS_ACTIVE_MAX)
            
            # if the max active orders are already put in, and are still active, there is nothing left to do.
            if num_open_orders >= DCA_.SAFETY_ORDERS_ACTIVE_MAX:
                # Max safety orders are already active.
                return

            for _, safety_order_dict in self.dca.safety_orders.items():
                for price, quantity in safety_order_dict.items():
                    price_max_prec   = self.get_pair_decimals(self.symbol_pair)
                    rounded_price    = self.round_decimals_down(price, price_max_prec)
                    rounded_quantity = self.round_decimals_down(quantity, self.get_max_volume_precision(symbol))
                    req_profit_price = self.round_decimals_down(self.__get_required_price(), price_max_prec)
                    buy_result       = self.limit_order(Trade.BUY, rounded_quantity, self.symbol_pair, rounded_price)

                    """ the next sell limit order should always be from the top of the safety orders.
                    For example:
                        Base order = 1,   $100
                        SO1        = 1,   $98.7
                        SO2        = 2.5, $96.5

                        Then our first sell order should be 1, for $100 + 0.5%
                        If SO1, is filled, the previous sell order should be cancelled and a new sell order should be placed: Base Order+SO1, required_price1
                        If SO2, is filled, the previous sell order should be cancelled and a new sell order should be placed: Base Order+SO1+SO2, required_price2
                    """

                    if self.has_result(buy_result):
                        G.log_file.print_and_log(message=f"buy_loop: limit order placed {self.symbol_pair} {buy_result[Dicts.RESULT]}", money=True)
                        
                        # keep track of the open order txid
                        self.save_open_buy_order_txid(buy_result, self.symbol_pair, req_profit_price)

                        """once the limit order was entered successfully, delete it from the excel sheet"""
                        self.dca.update_safety_orders()
                        num_orders_to_make -= 1
                    else:
                        G.log_file.print_and_log(message=f"buy_loop: {buy_result}", money=True)

                if num_orders_to_make <= 0:
                    break
        except Exception as e:
            G.log_file.print_and_log(e=e)
        return

    def __update_bought_set(self):
        """Get all the symbol names from the EXCEL_FILES_DIRECTORY
            and create the set of coins we are currently buying."""
        bought_set = set()

        # iterate through all files in EXCEL_FILES_DIRECTORY
        for filename in glob.iglob(EXCEL_FILES_DIRECTORY+"/*"):
            # get the symbol name
            symbol = filename.split("/")[2].split("\\")[1].replace(".xlsx", "")

            if symbol[-4:] == StableCoins.ZUSD:
                symbol = symbol[:-4]
            elif symbol[-3:] == StableCoins.USD:
                symbol = symbol[:-3]

            bought_set.add(symbol)
        return bought_set

    def __update_completed_trades(self, symbol: str) -> None:
        """
        If the sell order was filled, cancel all buy orders, 
        remove symbol from bought_list, delete excel_file. 
        
        """
        symbol_pair = self.get_tradable_asset_pair(symbol)
        filename    = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        
        if not os.path.exists(filename):
            return
        
        filled_sell_order_txids = dict()
        self.trade_history      = self.get_trades_history()
        df                      = pd.read_excel(filename, SheetNames.OPEN_SELL_ORDERS)
        
        for trade_txid, dictionary in self.trade_history[Dicts.RESULT][Data.TRADES].items():
            filled_sell_order_txids[dictionary[Data.ORDER_TXID]] = trade_txid

        """
        If the sell order has been filled, we have sold the coin for a profit.
        The things left to do is:
          1. cancel any remaining buy order
          2. delete the excel file
          3. remove symbol from bought_set
          4. start the process all over again!
        """
        for sell_order_txid in df[TXIDS].to_list():
            if sell_order_txid in filled_sell_order_txids.keys():
                # the sell order has filled and we have completed the entire process!!!
                open_buy_orders = pd.read_excel(filename, SheetNames.OPEN_BUY_ORDERS)

                for txid in open_buy_orders[TXIDS].to_list():
                    self.cancel_order(txid)
                    if os.path.exists(filename):
                        os.remove(filename)
        return

    def __update_filled_orders(self, symbol: str) -> None:
        """
        Updates the open_buy_orders sheet if a buy limit order has been filled.
        Accomplishes this by checking to see if the txid exists in the trade history list.

        1. Read all txids from txids.xlsx file into DataFrame.
        2. For every txid in the dataframe, check if the associated order has been filled.
        3. If the limit buy order has been filled, update the AVERAGE_PRICES_FILE with the new average and new quantity.
        
        Note: Function is called only once inside of the buy loop.
        
        """
        symbol_pair = self.get_tradable_asset_pair(symbol)
        filename    = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        
        if not os.path.exists(filename):
            return
        
        filled_trades_order_txids = dict()
        self.trade_history        = self.get_trades_history()
        df                        = pd.read_excel(filename, SheetNames.OPEN_BUY_ORDERS)
        
        for trade_txid, dictionary in self.trade_history[Dicts.RESULT][Data.TRADES].items():
            filled_trades_order_txids[dictionary[Data.ORDER_TXID]] = trade_txid

        for open_order_txid in df[TXIDS].to_list():
            if open_order_txid in filled_trades_order_txids.keys():
                # if the txid is in the trade history, the order was filled.
                self.sell.start(symbol_pair)
        return


    def update_buy_list(self) -> None:
        """Get all names that are in excel_files and add them to the Buy_.LIST.
        Note: if a user creates a new buy list in the config.txt file without completing previous trades,
        the bot will add the previous trades to the new buy list in an attempt to complete them.
        
        """
        for filename in glob.iglob(EXCEL_FILES_DIRECTORY+"/*"):
            # get the symbol name
            symbol = filename.split("/")[2].split("\\")[1].replace(".xlsx", "")

            if symbol[-4:] == StableCoins.ZUSD:
                symbol = symbol[:-4]
            elif symbol[-3:] == StableCoins.USD:
                symbol = symbol[:-3]

            if symbol not in Buy_.LIST:
                Buy_.LIST.append(symbol)
        return

##################################################################################################################################
### BUY_LOOP
##################################################################################################################################

    def buy_loop(self) -> None:
        """The main function for trading coins."""
        
        self.__init_loop_variables()
        bought_set = set()

        while True:
            for symbol in Buy_.LIST:
                self.__update_filled_orders(symbol)
                self.__update_completed_trades(symbol)
            try:
                bought_set = self.__update_bought_set()
                self.wait(message=f"buy_loop: Waiting till {self.__get_buy_time()} to buy", timeout=Buy_.TIME_MINUTES*60)

                for symbol in Buy_.LIST:
                    try:
                        self.wait(message=f"buy_loop: checking {symbol}", timeout=Nap.LONG)
                        self.__set_pre_buy_variables(symbol)
                        
                        # if symbol is in the bought list, we don't care if it is a good time to buy or not, we need to manage it
                        if not self.is_buy and symbol not in bought_set:
                            continue

                        self.__set_post_buy_variables(symbol)
                        self.__place_limit_orders(symbol)
                    except Exception as e:
                        G.log_file.print_and_log(message="buy_loop:", e=e)
                        continue
            except Exception as e:
                G.log_file.print_and_log(message="buy_loop:", e=e)
        return


# 10-26-21 buy list
# ['ATOMUSD', 'XTZUSD', 'XMRUSD', 'CRVUSD', 'KAVAUSD', 'TBTCUSD']