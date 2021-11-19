
"""
buy.py - Buys coin on kraken exchange based on users config file.

1. Have a list of coins that you want to buy.
2. Pull data from trading view based on 3c settings.
3. Make decision on whether to buy or not.
4. After base order is filled, create sell limit order at % higher
5. every time a safety order is filled, cancel current sell limit order and create a new sell limit order

"""

import datetime
import time

from pprint                    import pprint
from kraken_files.kraken_enums import *
from util.globals              import G
from bot_features.base         import Base
from bot_features.dca          import DCA
from bot_features.sell         import Sell
from bot_features.tradingview  import TradingView
from my_sql.sql                import SQL

x_list   = ['XETC', 'XETH', 'XLTC', 'XMLN', 'XREP', 'XXBT', 'XXDG', 'XXLM', 'XXMR', 'XXRP', 'XZEC']
reg_list = ['ETC',  'ETH',  'LTC',  'MLN',  'REP',  'XBT',  'XDG',  'XLM',  'XMR',  'XRP',  'ZEC' ]


class Buy(Base, TradingView):
    def __init__(self, parameter_dict: dict) -> None:
        super().__init__(parameter_dict)
        self.account_balance:         dict        = { }
        self.kraken_assets_dict:      dict        = { }
        self.exception_list:          list        = ["XTZ"]
        self.bid_price:               float       = 0.0
        self.quantity_to_buy:         float       = 0.0
        self.order_min:               float       = 0.0
        self.symbol_pair:             str         = ""
        self.is_buy:                  bool        = False
        self.dca:                     DCA         = None
        self.sell:                    Sell        = Sell(parameter_dict)
        self.sql:                     SQL         = SQL()
        return

    def __init_loop_variables(self) -> None:
        """Initialize variables for the buy_loop."""
        self.kraken_assets_dict = self.get_asset_info()[Dicts.RESULT]
        self.account_balance    = self.get_parsed_account_balance()
        self.asset_pairs_dict   = self.get_all_tradable_asset_pairs()[Dicts.RESULT]
        
        self.__init_buy_set()
        self.__set_future_time()
        
        print(f"Account value: ${self.__get_account_value()}")
        return

    def __get_buy_time(self) -> str:
        """Returns the next time to buy as specified in the config file."""
        return ( datetime.timedelta(minutes=Buy_.TIME_MINUTES) + datetime.datetime.now() ).strftime("%H:%M:%S")

    def __set_pre_buy_variables(self, symbol: str) -> None:
        """Sets the buy variables for each symbol."""
        try:
            self.symbol_pair = self.get_tradable_asset_pair(symbol)
            self.bid_price   = self.get_bid_price(self.symbol_pair)
            alt_name         = self.get_alt_name(symbol)
            self.is_buy      = self.is_strong_buy(alt_name+StableCoins.USD)
        except Exception as e:
            G.log_file.print_and_log(e=e)
        return

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

    def __place_base_order(self, order_min: float, symbol_pair: str) -> dict:
        """
        Place the base order for the coin we want to trade.
        The base order should be a market order only!
        
        """
        return self.market_order(Trade.BUY, order_min, symbol_pair)
    
    def __place_safety_orders(self, symbol: str) -> None:
        """Place safety orders."""
        sql = SQL()
        
        for price, quantity in self.dca.safety_orders.items():
            try:
                sql_req_price      = sql.con_get_required_price("safety_orders", self.symbol_pair)
                price_max_prec     = self.get_pair_decimals(self.symbol_pair)
                rounded_price      = self.round_decimals_down(price, price_max_prec)
                rounded_quantity   = self.round_decimals_down(quantity, self.get_max_volume_precision(symbol)) # put this in its own max_vol_prec
                req_price          = self.round_decimals_down(sql_req_price, price_max_prec)
                limit_order_result = self.limit_order(Trade.BUY, rounded_quantity, self.symbol_pair, rounded_price)

                if self.has_result(limit_order_result):
                    G.log_file.print_and_log(message=f"buy_loop: safety order placed {self.symbol_pair} {limit_order_result[Dicts.RESULT][Dicts.DESCR][Dicts.ORDER]}", money=True)
                    
                    try:
                        obo_txid         = limit_order_result[Dicts.RESULT][Data.TXID][0]
                        profit_potential = sql.con_get_profit("safety_orders", f"WHERE symbol_pair='{self.symbol_pair}' AND order_placed=false LIMIT 1").fetchone()[0]
                    except Exception as e:
                        print(e)
                    
                    # change order_placed to true in safety_orders table
                    sql.con_update_set("safety_orders", "order_placed=true", "order_placed=false LIMIT 1")
                    
                    # store open_buy_order row
                    sql.con_insert(f"INSERT INTO open_buy_orders {sql.obo_columns} VALUES ('{self.symbol_pair}', '{symbol}', {req_price}, {profit_potential}, false, '{obo_txid}')")
                else:
                    if limit_order_result[Dicts.ERROR][0] == KError.INSUFFICIENT_FUNDS:
                        G.log_file.print_and_log(f"buy_loop: {self.symbol_pair} Not enough USD to place remaining safety orders.")
                        return
                    elif limit_order_result[Dicts.ERROR][0] == KError.INVALID_VOLUME:
                        G.log_file.print_and_log(f"buy_loop: {self.symbol_pair} volume error.")
                    
                    G.log_file.print_and_log(message=f"buy_loop: {limit_order_result}", money=True)
            except Exception as e:
                G.log_file.print_and_log(e=e)
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
        sql = SQL()
        
        try:
            if self.symbol_pair not in sql.con_get_symbol_pairs():
                # If symbol_pair exists in database then the base order has already been placed!
                base_order_result = self.__place_base_order(self.order_min, self.symbol_pair)

                if self.has_result(base_order_result):
                    G.log_file.print_and_log(f"buy_loop: Base order filled: {base_order_result[Dicts.RESULT][Dicts.DESCR][Dicts.ORDER]}")
                    
                    base_order_qty = float(str(base_order_result[Dicts.RESULT][Dicts.DESCR][Dicts.ORDER]).split(" ")[1])
                    base_price     = self.__get_bought_price(base_order_result)
                    self.dca       = DCA(self.symbol_pair, symbol, base_order_qty, base_price)
                    
                    # upon placing the base_order, pass in the txid into dca to write to db
                    self.sell.place_sell_limit_base_order(self.symbol_pair, symbol, base_price, base_order_qty)
                else:
                    G.log_file.print_and_log(f"buy_loop: {self.symbol_pair} can't place base order: {base_order_result[Dicts.ERROR]}")
                    return
            else:
                # Symbol is in EXCEL_DIRECTORY therefore, we have bought it before.
                # Load up the .xlsx file and continue to place safety orders
                self.dca = DCA(self.symbol_pair, symbol, 0, 0)
            
            num_open_orders = sql.con_get_open_buy_orders(self.symbol_pair)
            
            # if the max active orders are already put in, and are still active, there is nothing left to do.
            if num_open_orders < DCA_.SAFETY_ORDERS_ACTIVE_MAX:
                self.__place_safety_orders(symbol)
        except Exception as e:
            G.log_file.print_and_log(e=e)
        return

    def __update_bought_set(self) -> set:
        """Get all the symbol names from the database
            and create the set of coins we are currently buying."""
        bought_set = set()
        sql        = SQL()
        
        sql.create_db_connection()
        result_set = sql.query("SELECT symbol_pair FROM safety_orders")
        result_set.close()
        sql.close_db_connection()
        
        for symbol in result_set.fetchall():
            bought_set.add(symbol[0])
        return bought_set

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
        # print("updating completed trades")
        
        try:
            symbol_pair           = self.get_tradable_asset_pair(symbol)
            bought_set            = set()
            open_sell_order_txids = set()
            sql                   = SQL()
            
            result_set = sql.con_query(f"SELECT symbol_pair FROM safety_orders WHERE symbol_pair='{symbol_pair}'")
            
            if result_set.rowcount <= 0:
                return
            
            for symbol in result_set.fetchall():
                bought_set.add(symbol[0])
            
            if symbol_pair not in bought_set:
                return
            
            time.sleep(1)
            filled_sell_order_txids = dict()
            trade_history           = self.get_trades_history()

            if not self.has_result(trade_history):
                return

            result_set = sql.con_query(f"SELECT oso_txid FROM open_sell_orders WHERE symbol_pair='{symbol_pair}' AND filled=false")
            
            for txid in result_set.fetchall():
                open_sell_order_txids.add(txid[0])

            for trade_txid, dictionary in trade_history[Dicts.RESULT][Data.TRADES].items():
                filled_sell_order_txids[dictionary[Data.ORDER_TXID]] = trade_txid

            for sell_order_txid in open_sell_order_txids:
                if sell_order_txid[0] in filled_sell_order_txids.keys():
                    # the sell order has filled and we have completed the entire process!!!
                    result_set = sql.con_query(f"SELECT profit FROM open_sell_orders WHERE symbol_pair='{symbol_pair}' AND filled=false")        
                    profit     = result_set.fetchall()
                    
                    result_set = sql.con_query(f"SELECT obo_txid FROM open_buy_orders WHERE symbol_pair='{symbol_pair}' AND filled=false")
                    open_buy_orders = result_set.fetchall()
                    
                    for txid in open_buy_orders:
                        self.cancel_order(txid[0])
                        
                    # remove rows associated with symbol_pair from all tables
                    sql.con_delete(SQLTable.SAFETY_ORDERS,    symbol_pair)
                    sql.con_delete(SQLTable.OPEN_BUY_ORDERS,  symbol_pair)
                    sql.con_delete(SQLTable.OPEN_SELL_ORDERS, symbol_pair)
                    
                    print(f"{symbol_pair} trade complete, profit: {profit}")
        except Exception as e:
            G.log_file.print_and_log(e=e)
        return

    def __update_open_buy_orders(self, symbol: str) -> None:
        """
        Updates the open_buy_orders sheet if a buy limit order has been filled.
        Accomplishes this by checking to see if the txid exists in the trade history list.

        1. Read all txids from txids.xlsx file into DataFrame.
        2. For every txid in the dataframe, check if the associated order has been filled.
        3. If the limit buy order has been filled, update the AVERAGE_PRICES_FILE with the new average and new quantity.
        
        Note: Function is called only once inside of the buy loop.
        
        """
        
        # print("updating open buy orders")
        
        try:
            symbol_pair = self.get_tradable_asset_pair(symbol)
            txid_set    = set()
            sql         = SQL()
            
            result_set = sql.con_query(f"SELECT symbol_pair FROM safety_orders WHERE symbol_pair='{symbol_pair}' LIMIT 1")
    
            if result_set.rowcount <= 0:
                return
            
            if symbol_pair not in [ x[0] for x in result_set.fetchall() ]:
                return 
            
            time.sleep(1)
            filled_trades_order_txids = dict()
            trade_history        = self.get_trades_history()
            
            if not self.has_result(trade_history):
                return
            
            result_set = sql.con_query(f"SELECT obo_txid FROM open_buy_orders WHERE symbol_pair='{symbol_pair}' AND filled=false")
            
            for txid in result_set.fetchall():
                txid_set.add(txid[0])
            
            for trade_txid, dictionary in trade_history[Dicts.RESULT][Data.TRADES].items():
                filled_trades_order_txids[dictionary[Data.ORDER_TXID]] = trade_txid
            
            for obo_txid in txid_set:
                if obo_txid in filled_trades_order_txids.keys():
                    # if the txid is in the trade history, the order open_buy_order was filled.
                    
                    # Everytime an open_buy_order is filled we need to
                        # 1. Set filled=true in open_buy_orders table
                        # 2. Cancel the open_sell_order on 'symbol_pair'
                        # 3. Place a new sell order
                    self.sell.start(symbol_pair, symbol, obo_txid)
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
        sql     = SQL()
        
        for symbol in self.get_buy_long():
            if symbol in reg_list:
                buy_set.add("X" + symbol)
            else:
                buy_set.add(symbol)
        
        bought_set = sql.con_get_symbols()
        Buy_.SET   = set(sorted(bought_set.union(buy_set)))
        print("Buy_.SET:", Buy_.SET)
        return

    def __set_buy_set(self, bought_set: set) -> None:
        """Once every ... minutes, run this function. 
        Add to the buy_list with these coins."""
        result_set = set()
        try:
            if self.future_time < datetime.datetime.now().strftime("%H:%M:%S"):
                for symbol in self.get_buy_long():
                    if symbol in reg_list:
                        result_set.add("X" + symbol)
                    else:
                        result_set.add(symbol)

                self.__set_future_time()
                Buy_.SET = set(sorted(result_set.union(bought_set)))
                print("Buy_.SET:", Buy_.SET)
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
            time.sleep(1)
            order_result = self.query_orders_info(buy_result[Dicts.RESULT][Data.TXID][0])
            if self.has_result(order_result):
                for txid in order_result[Dicts.RESULT]:
                    for key, value in order_result[Dicts.RESULT][txid].items():
                        if key == Data.PRICE:
                            bought_price = float(value)
                            break
        return bought_price


    def nuke_and_restart(self):
        sql = SQL()
        sql.create_db_connection()
        sql.drop_all_tables()
        sql.create_tables()
        sql.close_db_connection()
        self.cancel_all_orders()

##################################################################################################################################
### BUY_LOOP
##################################################################################################################################

    def buy_loop(self) -> None:
        """The main function for trading coins."""
        self.__init_loop_variables()
        bought_set = set()
        
        self.nuke_and_restart()

        while True:
            bought_set = self.__update_bought_set()
            self.wait(message=f"buy_loop: Waiting till {self.__get_buy_time()} to buy", timeout=Buy_.TIME_MINUTES*60)
            self.__set_buy_set(bought_set)

            Buy_.SET = set()
            Buy_.SET.add("CRV")
            
            for symbol in Buy_.SET:
                self.wait(message=f"buy_loop: checking {symbol}", timeout=Nap.LONG)
                self.__update_open_buy_orders(symbol)
                self.__update_completed_trades(symbol)
                
                self.__set_pre_buy_variables(symbol)
                # if symbol is in the bought list, we don't care if it is a good time to buy or not, we need to manage it
                # if not self.is_buy and symbol not in bought_set: continue
                self.__set_post_buy_variables(symbol)
                self.__place_limit_orders(symbol)
        return
    