
"""
buy.py - Buys coin on kraken exchange based on users config file.

1. Have a list of coins that you want to buy.
2. Pull data from trading view based on 3c settings.
3. Make decision on whether to buy or not.
4. After base order is filled, create sell limit order at % higher
5. every time a safety order is filled, cancel current sell limit order and create a new sell limit order

"""

import datetime
import os
from typing import Dict
import pandas as pd
import glob
import sys
import time

from pprint                    import pprint
from kraken_files.kraken_enums import *
from util.globals              import G
from bot_features.base         import Base
from bot_features.dca          import DCA
from bot_features.sell         import Sell
from bot_features.tradingview  import TradingView


x_list   = ['XETC', 'XETH', 'XLTC', 'XMLN', 'XREP', 'XXBT', 'XXDG', 'XXLM', 'XXMR', 'XXRP', 'XZEC']
reg_list = ['ETC',  'ETH',  'LTC',  'MLN',  'REP',  'XBT',  'XDG',  'XLM',  'XMR',  'XRP',  'ZEC' ]


class Buy(Base, TradingView):
    def __init__(self, parameter_dict: dict) -> None:
        super().__init__(parameter_dict)
        
        self.account_balance:         dict        = { }
        self.kraken_assets_dict:      dict        = { }
        self.trade_history:           dict        = { }
        self.exception_list:          list        = ["XTZ"]
        self.bid_price:               float       = 0.0
        self.quantity_to_buy:         float       = 0.0
        self.order_min:               float       = 0.0
        self.symbol_pair:             str         = ""
        self.is_buy:                  bool        = False
        self.dca:                     DCA         = None
        self.sell:                    Sell        = Sell(parameter_dict)
        return

    def __init_loop_variables(self) -> None:
        """Initialize variables for the buy_loop."""
        self.kraken_assets_dict = self.get_asset_info()[Dicts.RESULT]
        self.account_balance    = self.get_parsed_account_balance()
        self.asset_pairs_dict   = self.get_all_tradable_asset_pairs()[Dicts.RESULT]
        self.__create_excel_directory()
        self.__init_buy_set()
        self.__set_future_time()
        return

    def __get_buy_time(self) -> str:
        """Returns the next time to buy as specified in the config file."""
        return ( datetime.timedelta(minutes=Buy_.TIME_MINUTES) + datetime.datetime.now() ).strftime("%H:%M:%S")

    def __create_excel_directory(self) -> None:
        """Create the excel_files directory."""
        if not os.path.exists(EXCEL_FILES_DIRECTORY):
            os.mkdir(EXCEL_FILES_DIRECTORY)
        return

    def __set_pre_buy_variables(self, symbol: str) -> None:
        """Sets the buy variables for each symbol."""
        try:
            self.wait(message=f"buy_loop: checking {symbol}", timeout=Nap.LONG)

            self.symbol_pair = self.get_tradable_asset_pair(symbol)
            self.bid_price   = self.get_bid_price(self.symbol_pair)
            alt_name         = self.get_alt_name(symbol)
            self.is_buy      = self.is_strong_buy(alt_name+StableCoins.USD)
        except Exception as e:
            G.log_file.print_and_log(e=e)
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
        count           = 0
        alt_symbol_pair = self.get_alt_name(symbol) + StableCoins.USD

        if self.has_result(self.open_orders):
            for _, dictionary in self.open_orders[Dicts.RESULT][Dicts.OPEN].items():
                if dictionary[Dicts.DESCR][Data.PAIR] == alt_symbol_pair:
                    count += 1
        return count

    def __set_post_buy_variables(self, symbol: str) -> None:
        """Sets variables in order to make an buy order."""
        try:
            self.wait(timeout=Nap.LONG)
            self.order_min           = self.get_order_min(symbol)
            self.pair_decimals       = self.get_pair_decimals(self.symbol_pair)
            self.open_orders         = self.get_open_orders()
        except Exception as e:
            G.log_file.print_and_log(e=e)
        return

    def __get_required_price(self):
        filename = EXCEL_FILES_DIRECTORY + "/" + self.symbol_pair + ".xlsx"
        df       = pd.read_excel(filename, SheetNames.SAFETY_ORDERS)
        return float(df[SOColumns.REQ_PRICE].to_list()[0])

    def __place_base_order(self, order_min: float, symbol_pair: str) -> dict:
        """
        Place the base order for the coin we want to trade.
        The base order should be a market order only!
        
        """        
        return self.market_order(Trade.BUY, order_min, symbol_pair) 

    def __place_safety_orders(self, symbol: str, num_orders_to_make: int) -> None:
        for _, safety_order_dict in self.dca.safety_orders.items():
            for price, quantity in safety_order_dict.items():
                try:
                    price_max_prec     = self.get_pair_decimals(self.symbol_pair)
                    rounded_price      = self.round_decimals_down(price, price_max_prec)
                    rounded_quantity   = self.round_decimals_down(quantity, self.get_max_volume_precision(symbol))
                    req_profit_price   = self.round_decimals_down(self.__get_required_price(), price_max_prec)
                    limit_order_result = self.limit_order(Trade.BUY, rounded_quantity, self.symbol_pair, rounded_price)

                    if self.has_result(limit_order_result):
                        G.log_file.print_and_log(message=f"buy_loop: limit order placed {self.symbol_pair} {limit_order_result[Dicts.RESULT]}", money=True)
                        
                        # keep track of the open order txid
                        self.save_open_buy_order_txid(limit_order_result, self.symbol_pair, req_profit_price)

                        # once the limit order was entered successfully, delete it from the excel sheet.
                        self.dca.update_safety_orders()
                        num_orders_to_make -= 1
                    else:
                        if limit_order_result[Dicts.ERROR][0] == KError.INSUFFICIENT_FUNDS:
                            G.log_file.print_and_log(f"buy_loop: {self.symbol_pair} Not enough USD to place remaining safety orders.")
                            return

                        G.log_file.print_and_log(message=f"buy_loop: {limit_order_result}", money=True)
                except Exception as e:
                    G.log_file.print_and_log(e=e)
            
            if num_orders_to_make <= 0:
                break
        return

    def __place_limit_orders(self, symbol: str) -> None:
        """
        The Base order will be a market order but all the safety orders will be a limit order.
        Place the safety orders that were set inside of the DCA class.
        If the limit order was entered successfully, update the excel sheet by removing the order we just placed.

        The next sell limit order should always be from the top of the safety orders,
        
        For example:
            Base order = 1,   $100
            SO1        = 1,   $98.7
            SO2        = 2.5, $96.5

            Then our first sell order should be 1, for $100 + 0.5%
            If SO1, is filled, the previous sell order should be cancelled and a new sell order should be placed: Base Order+SO1, required_price1
            If SO2, is filled, the previous sell order should be cancelled and a new sell order should be placed: Base Order+SO1+SO2, required_price2
        
        """
        try:
            if symbol not in self.__get_symbols_from_directory():
                # if symbol_pair exists in excel_files directory then the base order has already been placed!
                base_order_result = self.__place_base_order(self.order_min, self.symbol_pair)

                if self.has_result(base_order_result):
                    G.log_file.print_and_log(f"buy_loop: Base order filled: {base_order_result[Dicts.RESULT]}")
                    
                    base_order_qty = float(str(base_order_result[Dicts.RESULT][Dicts.DESCR]['order']).split(" ")[1])
                    base_price     = self.__get_bought_price(base_order_result)
                    
                    print("base_order_qty:", base_order_qty)
                    print("base_price:",     base_price)
                    
                    self.dca       = DCA(self.symbol_pair, base_order_qty, base_price)
                    self.sell.place_sell_limit_base_order(self.symbol_pair, base_price, base_order_qty) # place sell order for base order
                else:
                    G.log_file.print_and_log(f"buy_loop: {self.symbol_pair} can't place base order: {base_order_result[Dicts.ERROR]}")
                    return
            else:
                # symbol is in EXCEL_DIRECTORY therefore, we have bought it before.
                # load up the .xlsx file and continue to place safety orders
                self.dca = DCA(self.symbol_pair, -1, -1)
                
            num_open_orders    = self.__get_open_orders_on_symbol_pair(symbol)
            num_orders_to_make = abs(num_open_orders-DCA_.SAFETY_ORDERS_ACTIVE_MAX)
            
            # if the max active orders are already put in, and are still active, there is nothing left to do.
            if num_open_orders < DCA_.SAFETY_ORDERS_ACTIVE_MAX:
                self.__place_safety_orders(symbol, num_orders_to_make)
        except Exception as e:
            G.log_file.print_and_log(e=e)
        return

    def __get_symbols_from_directory(self) -> set:
        """Get the symbol from EXCEL_FILES_DIRECTORY."""
        bought_set = set()
        try:
            for filename in glob.iglob(EXCEL_FILES_DIRECTORY+"/*"):
                if sys.platform == "win32":
                    symbol = filename.split("/")[2].split("\\")[1].replace(".xlsx", "")
                else:
                    symbol = filename.split("/")[3].replace(".xlsx", "")

                if symbol[:-3] not in self.exception_list:
                    if symbol[-4:] == StableCoins.ZUSD:
                        symbol = symbol[:-4]
                    elif symbol[-3:] == StableCoins.USD:
                        symbol = symbol[:-3]
                else:
                    symbol = symbol[:-3] 
                
                bought_set.add(symbol)
        except Exception as e:
            G.log_file.print_and_log(e=e)
        return bought_set

    def __update_bought_set(self) -> set:
        """Get all the symbol names from the EXCEL_FILES_DIRECTORY
            and create the set of coins we are currently buying."""
        return self.__get_symbols_from_directory()

    def __update_completed_trades(self, symbol: str) -> None:
        """
        If the sell order was filled, cancel all buy orders, 
        remove symbol from bought_list, delete excel_file. 
        
        If the sell order has been filled, we have sold the coin for a profit.
        The things left to do is:
          1. cancel any remaining buy order
          2. delete the excel file
          3. remove symbol from bought_set
          4. start the process all over again!
        
        """
        try:
            filename = EXCEL_FILES_DIRECTORY + "/" + self.get_tradable_asset_pair(symbol) + ".xlsx"
            
            if not os.path.exists(filename):
                return
            
            time.sleep(1)
            filled_sell_order_txids = dict()
            self.trade_history      = self.get_trades_history()
            df                      = pd.read_excel(filename, SheetNames.OPEN_SELL_ORDERS)

            if not self.has_result(self.trade_history):
                return

            for trade_txid, dictionary in self.trade_history[Dicts.RESULT][Data.TRADES].items():
                filled_sell_order_txids[dictionary[Data.ORDER_TXID]] = trade_txid

            for sell_order_txid in df[TXIDS].to_list():
                if sell_order_txid in filled_sell_order_txids.keys():
                    # the sell order has filled and we have completed the entire process!!!
                    open_buy_orders = pd.read_excel(filename, SheetNames.OPEN_BUY_ORDERS)

                    for txid in open_buy_orders[TXIDS].to_list():
                        self.cancel_order(txid)
                        if os.path.exists(filename):
                            os.remove(filename)
        except Exception as e:
            G.log_file.print_and_log(e=e)
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
        try:
            symbol_pair = self.get_tradable_asset_pair(symbol)
            filename    = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
            
            if not os.path.exists(filename):
                return
            
            time.sleep(1)
            filled_trades_order_txids = dict()
            self.trade_history        = self.get_trades_history()
            df                        = pd.read_excel(filename, SheetNames.OPEN_BUY_ORDERS)
            
            if not self.has_result(self.trade_history):
                return

            for trade_txid, dictionary in self.trade_history[Dicts.RESULT][Data.TRADES].items():
                filled_trades_order_txids[dictionary[Data.ORDER_TXID]] = trade_txid

            for open_order_txid in df[TXIDS].to_list():
                if open_order_txid in filled_trades_order_txids.keys():
                    # if the txid is in the trade history, the order was filled.
                    self.sell.start(symbol_pair)
        except Exception as e:
            G.log_file.print_and_log(e=e)
        return

    def __get_future_time(self) -> str:
        result = datetime.timedelta(minutes=60) + datetime.datetime.now()
        return result.strftime("%H:%M:%S")

    def __set_future_time(self) -> None:
        self.future_time = self.__get_future_time()
        return

    def __init_buy_set(self) -> None:
        """
        On startup, run analysis on all tradable coins through kraken exchange and create set of the buy coins.
        Combine this set with the list of coins we are still in the middle of a deal with.
        Set Buy_.SET to these coins.
        """
        buy_set = set()
        for symbol in self.get_buy_long():
            if symbol in reg_list:
                buy_set.add("X" + symbol)
            else:
                buy_set.add(symbol)

        print("buy_set:", sorted(buy_set))
        bought_set = self.__get_symbols_from_directory()
        Buy_.SET   = sorted(bought_set.union(buy_set))
        return

    def __set_buy_set(self, bought_set: set) -> None:
        """Once every hour, run this function. 
        Add to the buy_list with these coins."""
        result_set = set()
        try:
            if self.future_time < datetime.datetime.now().strftime("%H:%M:%S"):
                for symbol in self.get_buy_long():
                    if symbol in reg_list:
                        result_set.add("X" + symbol)
                    else:
                        result_set.add(symbol)

                Buy_.SET = sorted(result_set.union(bought_set))
                self.__set_future_time()
        except Exception as e:
            G.log_file.print_and_log(e=e)
        return
    
    def __get_account_value(self) -> float:
        """Get account value by adding all coin quantities together and putting in USD terms."""
        total   = 0.0
        account = self.get_account_balance()

        if self.has_result(account):
            for symbol, quantity in account[Dicts.RESULT].items():
                quantity = float(quantity)
                if float(quantity) > 0:
                    if symbol in x_list:
                        symbol = symbol[1:]
                    if symbol == StableCoins.ZUSD or symbol == StableCoins.USD or symbol == StableCoins.USDT:
                        total += quantity
                    else:
                        bid_price = self.get_bid_price(symbol+StableCoins.USD)
                        value = bid_price * quantity
                        total += value
        return round(total, 2)

    def __get_bought_price(self, buy_result: dict) -> float:
        """Parses the buy_result to get the entry_price or bought_price of the base order."""
        bought_price = 0
        order_result = None
        
        if self.has_result(buy_result):
            time.sleep(5)
            order_result = self.query_orders_info(buy_result[Dicts.RESULT][Data.TXID][0])
            # pprint(order_result)
            if self.has_result(order_result):
                for txid in order_result[Dicts.RESULT]:
                    for key, value in order_result[Dicts.RESULT][txid].items():
                        if key == Data.PRICE:
                            bought_price = float(value)
                            break
        if bought_price == 0:
            # something went wrong
            # pprint(buy_result) # {'error': [], 'result': {'txid': ['OY2H7D-LPG7B-NHZLP4'], 'descr': {'order': 'buy 0.00010000 TBTCUSD @ market'}}}
            # print()
            pprint(order_result)
        return bought_price

##################################################################################################################################
### BUY_LOOP
##################################################################################################################################

    def buy_loop(self) -> None:
        """The main function for trading coins."""
        self.__init_loop_variables()
        bought_set = set()
        print(f"Account value: ${self.__get_account_value()}")
        
        while True:
            for symbol in Buy_.SET:
                self.__update_filled_orders(symbol)
                self.__update_completed_trades(symbol)

                bought_set = self.__update_bought_set()
                self.wait(message=f"buy_loop: Waiting till {self.__get_buy_time()} to buy", timeout=Buy_.TIME_MINUTES*60)
                self.__set_buy_set(bought_set)

                for symbol in Buy_.SET:
                        # something is wrong with Dogecoin
                        if symbol == "XXDG":
                            continue

                        self.__set_pre_buy_variables(symbol)
                        
                        # if symbol is in the bought list, we don't care if it is a good time to buy or not, we need to manage it
                        if not self.is_buy and symbol not in bought_set:
                            continue

                        self.__set_post_buy_variables(symbol)
                        self.__place_limit_orders(symbol)
                    # except Exception as e:
                        # G.log_file.print_and_log(message="buy_loop:", e=e)
                        # continue
        return
