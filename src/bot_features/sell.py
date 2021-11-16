
"""sell.py: Sells coin on kraken exchange based on users config file."""

from mysql.connector.cursor import MySQLCursor, MySQLCursorBuffered
import pandas as pd
import os

from pprint                    import pprint
from kraken_files.kraken_enums import *
from util.globals              import G
from bot_features.base         import Base
from my_sql.sql                import SQL

class Sell(Base):
    def __init__(self, parameter_dict: dict) -> None:
        super().__init__(parameter_dict)
        self.asset_pairs_dict:  dict = self.get_all_tradable_asset_pairs()[Dicts.RESULT]
        self.sell_order_placed: bool = False

    def __save_to_open_buy_orders(self, symbol_pair: str, df2: pd.DataFrame) -> None:
        """Write the DataFrame to an excel file."""
        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        
        if not os.path.exists(filename):
            raise Exception(f"__save_to_open_buy_orders: {filename} does not exist!")         
        
        df1 = pd.read_excel(filename, SheetNames.SAFETY_ORDERS)
        df3 = pd.read_excel(filename, SheetNames.OPEN_SELL_ORDERS)

        with pd.ExcelWriter(filename, engine=OPENPYXL, mode=FileMode.WRITE_TRUNCATE) as writer:
            df1.to_excel(writer, SheetNames.SAFETY_ORDERS,    index=False)
            df2.to_excel(writer, SheetNames.OPEN_BUY_ORDERS,  index=False)
            df3.to_excel(writer, SheetNames.OPEN_SELL_ORDERS, index=False)
        return

    def __save_to_open_sell_orders(self, file_name: str, df3: pd.DataFrame) -> None:
        """Write the DataFrame to an excel file."""
        df1 = pd.read_excel(file_name, SheetNames.SAFETY_ORDERS)
        df2 = pd.read_excel(file_name, SheetNames.OPEN_BUY_ORDERS)

        with pd.ExcelWriter(file_name, engine=OPENPYXL, mode=FileMode.WRITE_TRUNCATE) as writer:
            df1.to_excel(writer, SheetNames.SAFETY_ORDERS,    index=False)
            df2.to_excel(writer, SheetNames.OPEN_BUY_ORDERS,  index=False)
            df3.to_excel(writer, SheetNames.OPEN_SELL_ORDERS, index=False)
        return

    def __get_quantity_owned(self, symbol: str) -> float:
        """Gets the quantity of a coin owned."""
        account_balance = self.get_account_balance()
        if self.has_result(account_balance):
            account_balance = account_balance[Dicts.RESULT]
            for sym, qty in account_balance.items():
                if sym not in StableCoins.STABLE_COINS_LIST:
                    if sym in symbol:
                        return float(qty)
        return 0.0

    def __get_required_price(self, symbol_pair: str) -> float:
        """Get cell value from required_price column."""
        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        if not os.path.exists(filename):
            raise Exception(f"__get_required_price: {filename} does not exist!") 
        return float(pd.read_excel(filename, SheetNames.OPEN_BUY_ORDERS)[OBOColumns.REQ_PRICE][0])

    def __get_max_price_prec(self, symbol_pair: str) -> int:
        return self.get_max_price_precision(symbol_pair[:-4]) if StableCoins.ZUSD in symbol_pair else self.get_max_price_precision(symbol_pair[:-3])

    def __get_max_volume_prec(self, symbol_pair: str) -> int:
        return self.get_max_volume_precision(symbol_pair[:-4]) if StableCoins.ZUSD in symbol_pair else self.get_max_volume_precision(symbol_pair[:-3])

    def __cancel_open_sell_order(self, symbol_pair: str) -> None:
        """
        Open the sell_txids.xlsx file, cancel all sell orders by symbol name.
        
        """
        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"

        if not os.path.exists(filename):
            raise Exception(f"__cancel_open_sell_order: {filename} does not exist!")        
        
        txids_list = pd.read_excel(filename, SheetNames.OPEN_SELL_ORDERS)[TXIDS].to_list()

        # on first sell order, there will be no txid inside of the sell_order sheet,
        # therefore, this for loop is skipped.
        for txid in txids_list:
            self.cancel_order(txid)
            df = pd.read_excel(filename, SheetNames.OPEN_SELL_ORDERS)
            df = df[ df[TXIDS] == txid]
            self.__save_to_open_sell_orders(filename, df)
        return
    
    def __get_profit_from_sheet(self, symbol_pair: str, sheet_name: str) -> float:
        """
        Get the profit potential from the open_sell_orders tab.
        
        """
        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        
        if not os.path.exists(filename):
            raise Exception(f"__get_profit_from_sheet: {filename} does not exist!")        
        
        profit_list = pd.read_excel(filename, sheet_name)[OBOColumns.PROFIT].to_list()
        
        if len(profit_list) > 0:
            return float(profit_list[0])
        
        raise Exception(f"__get_profit_from_sheet: No profit cell in {sheet_name} sheet")


    def __place_sell_limit_order(self, symbol_pair: str) -> dict:
        """
        Place limit order to sell the coin.
        
        """
        required_price    = self.round_decimals_down(self.__get_required_price(symbol_pair), self.__get_max_price_prec(symbol_pair))
        max_prec          = self.__get_max_volume_prec(symbol_pair)
        qty_owned         = self.__get_quantity_owned(symbol_pair)
        qty_to_sell       = self.round_decimals_down(qty_owned, max_prec)
        sell_order_result = self.limit_order(Trade.SELL, qty_to_sell, symbol_pair, required_price)
        
        if self.has_result(sell_order_result):
            profit_potential = self.__get_profit_from_sheet(symbol_pair, SheetNames.OPEN_SELL_ORDERS)
            G.log_file.print_and_log(f"sell: limit order placed {symbol_pair} {sell_order_result[Dicts.RESULT][Dicts.DESCR][Dicts.ORDER]}, Profit Potential: ${profit_potential}")
        else:
            G.log_file.print_and_log(f"sell: {symbol_pair} {sell_order_result[Dicts.ERROR]}")
        return sell_order_result

    def __update_open_buy_orders(self, symbol_pair: str, filled_buy_order_txid: str) -> None:
        """If the first open_buy_order has been filled and the sell order has been placed successfully,
        we need to remove the first row in the open_buy_orders sheet as it is no longer open and needed 
        to place the next sell limit order."""

        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        
        if not os.path.exists(filename):
            raise Exception(f"__update_open_buy_orders: {filename} does not exist!")
        
        df = pd.read_excel(filename, SheetNames.OPEN_BUY_ORDERS)
        df.drop(0, inplace=True)
        self.__save_to_open_buy_orders(symbol_pair, df)

        # mark filled as true
        # get the txid of which order was filled, then use that as the key to mark as filled        
        # sql = SQL()
        # sql.create_db_connection()
        # result_set: MySQLCursorBuffered = sql.execute_query(f"SELECT * FROM open_buy_orders WHERE txid='{filled_buy_order_txid}'")
        
        # for x in result_set:
        #     sql.execute_update("INSERT INTO open_buy_orders SET filled=true WHERE filled=false")
        # sql.close_db_connection()
        return

    def __update_open_sell_orders_sheet(self, symbol_pair: str, order_result: dict, profit_potential: float) -> None:
        """log the sell order in sell_orders/txids.xlsx."""
        filename = EXCEL_FILES_DIRECTORY + "/" + symbol_pair + ".xlsx"
        
        if not os.path.exists(filename):
            raise Exception(f"__update_open_sell_orders_sheet: {filename} does not exist!")
        
        if not self.has_result(order_result):
            raise Exception(f"__update_open_sell_orders_sheet: {order_result}")
        
        df = pd.read_excel(filename, SheetNames.OPEN_SELL_ORDERS)
        df.loc[len(df.index), OSOColumns.TXIDS]    = order_result[Dicts.RESULT][Data.TXID][0]
        df.loc[len(df.index)-1, OSOColumns.PROFIT] = profit_potential
        
        self.__save_to_open_sell_orders(filename, df)
        return
    
    def __get_sell_order_txid(self, sell_order_result) -> str:
        if not self.has_result(sell_order_result):
            raise Exception(f"sell.__get_sell_order_txid: {sell_order_result}")        
        return sell_order_result[Dicts.RESULT][Data.TXID][0]
        
##################################################################
### Place sell order for base order only!
##################################################################
    def place_sell_limit_base_order(self, symbol_pair: str, entry_price: float, quantity: float) -> dict:
        """Create a sell limit order for the base order only!"""
        self.__cancel_open_sell_order(symbol_pair)
        
        required_price    = entry_price + (entry_price*DCA_.TARGET_PROFIT_PERCENT/100)
        required_price    = self.round_decimals_down(required_price, self.__get_max_price_prec(symbol_pair))
        sell_order_result = self.limit_order(Trade.SELL, quantity, symbol_pair, required_price)
        
        if self.has_result(sell_order_result):
            profit_potential = entry_price * quantity * DCA_.TARGET_PROFIT_PERCENT/100
            G.log_file.print_and_log(f"sell: limit order placed {symbol_pair} {sell_order_result[Dicts.RESULT][Dicts.DESCR][Dicts.ORDER]}, Profit Potential: ${profit_potential}")
            self.__update_open_sell_orders_sheet(symbol_pair, sell_order_result, profit_potential)
            
            sell_order_txid = sell_order_result[Dicts.RESULT][Data.TXID][0]
            
            sql = SQL()
            sql.create_db_connection()
            query = f"INSERT INTO open_sell_orders {sql.oso_columns} VALUES ('{symbol_pair}', {profit_potential}, false, false, '{sell_order_txid}')"
            sql.update(query)
            sql.close_db_connection()
        else:
            G.log_file.print_and_log(f"place_sell_limit_base_order: {symbol_pair} {sell_order_result[Dicts.ERROR]}")

        return sell_order_result
    
##################################################################
### Run the entire sell process for safety orders
##################################################################
    def start(self, symbol_pair: str, filled_buy_order_txid: str) -> None:
        """
        Everytime an open_buy_order is filled we need to
            1. Set filled=true in open_buy_orders table
            2. Cancel the open_sell_order on 'symbol_pair'
            3. Place a new sell order
            4. insert new sell order into open_sell_order table

        """
        sql = SQL()
        
        sql.create_db_connection()
        # 1. change filled=true in open_buy_orders table
        sql.update(f"UPDATE open_buy_orders SET filled=true WHERE \
            symbol_pair='{symbol_pair}' AND obo_txid='{filled_buy_order_txid}' AND filled=false LIMIT 1")
        sql.close_db_connection()
        
        # get profit from open_buy_orders table
        sql.create_db_connection()
        result_set = sql.query(f"SELECT profit FROM open_buy_orders WHERE obo_txid='{filled_buy_order_txid}'")
        sql.close_db_connection()
        
        # 2. cancel open_sell_order
        self.__cancel_open_sell_order(symbol_pair)


        # 3. change cancelled sell order to true in open_sell_orders
        sql.create_db_connection()
        sql.update(f"UPDATE open_sell_orders SET cancelled=true WHERE symbol_pair='{symbol_pair}' AND filled=false LIMIT 1")
        sql.close_db_connection()
        
        sell_order_result = self.__place_sell_limit_order(symbol_pair)
        sell_order_txid   = self.__get_sell_order_txid(sell_order_result)
        
        # insert sell order into sql
        profit_potential = result_set.fetchone()[0]
        sql.update(f"INSERT INTO open_sell_orders {sql.oso_columns} VALUES \
                               ('{symbol_pair}', {sell_order_txid}, {profit_potential}, false, false, '{sell_order_txid}')")
        sql.close_db_connection()

        self.__update_open_buy_orders(symbol_pair, filled_buy_order_txid)
        self.__update_open_sell_orders_sheet(symbol_pair, sell_order_result, profit_potential)
        return