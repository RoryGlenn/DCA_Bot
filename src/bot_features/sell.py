
"""sell.py: Sells coin on kraken exchange based on users config file."""

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

    def __get_max_price_prec(self, symbol_pair: str) -> int:
        return self.get_max_price_precision(symbol_pair[:-4]) if StableCoins.ZUSD in symbol_pair else self.get_max_price_precision(symbol_pair[:-3])

    def __get_max_volume_prec(self, symbol_pair: str) -> int:
        return self.get_max_volume_precision(symbol_pair[:-4]) if StableCoins.ZUSD in symbol_pair else self.get_max_volume_precision(symbol_pair[:-3])

    def __cancel_open_sell_order(self, symbol_pair: str) -> None:
        """
        Open the sell_txids.xlsx file, cancel all sell orders by symbol name.
        
        """
        
        txid_set = set()
        sql      = SQL()
        sql.create_db_connection()
        result_set = sql.query(f"SELECT oso_txid FROM open_sell_orders WHERE symbol_pair='{symbol_pair}' AND cancelled=false AND filled=false")
        sql.close_db_connection()
        
        for oso_txid in result_set.fetchall():
            txid_set.add(oso_txid[0])

        # on first sell order, there will be no txid inside of the sell_order sheet,
        # therefore, this for loop is skipped.
        for txid in txid_set:
            self.cancel_order(txid)
            sql.create_db_connection()
            result_set = sql.update(f"UPDATE open_sell_orders SET cancelled=true WHERE symbol_pair='{symbol_pair}' AND cancelled=false AND filled=false")
            sql.close_db_connection()
        return
    
    
    def __place_sell_limit_order(self, symbol_pair: str, filled_buy_order_txid: str) -> dict:
        """
        Place limit order to sell the coin.
        
        """
        sql = SQL()

        nonrounded_req_price = sql.con_get_required_price("safety_orders", symbol_pair)
        max_prec             = self.__get_max_price_prec(symbol_pair)
        required_price       = self.round_decimals_down(nonrounded_req_price, max_prec)
        max_prec             = self.__get_max_volume_prec(symbol_pair)
        qty_owned            = self.__get_quantity_owned(symbol_pair)
        qty_to_sell          = self.round_decimals_down(qty_owned, max_prec)
        sell_order_result    = self.limit_order(Trade.SELL, qty_to_sell, symbol_pair, required_price)
        
        if self.has_result(sell_order_result):
            sql.create_db_connection()
            result_set = sql.query(f"SELECT profit FROM open_buy_orders WHERE symbol_pair='{symbol_pair}' AND obo_txid='{filled_buy_order_txid}'")
            sql.close_db_connection()
            
            profit_potential = result_set.fetchone()[0] if result_set.rowcount > 0 else 0
            G.log_file.print_and_log(f"sell: limit order placed {symbol_pair} {sell_order_result[Dicts.RESULT][Dicts.DESCR][Dicts.ORDER]}, Profit Potential: ${profit_potential}")
        else:
            G.log_file.print_and_log(f"sell: {symbol_pair} {sell_order_result[Dicts.ERROR]}")
        return sell_order_result

    def __get_sell_order_txid(self, sell_order_result) -> str:
        if not self.has_result(sell_order_result):
            raise Exception(f"sell.__get_sell_order_txid: {sell_order_result}")        
        return sell_order_result[Dicts.RESULT][Data.TXID][0]
        
##################################################################
### Place sell order for base order only!
##################################################################
    def place_sell_limit_base_order(self, symbol_pair: str, symbol: str, entry_price: float, quantity: float) -> dict:
        """Create a sell limit order for the base order only!"""
        self.__cancel_open_sell_order(symbol_pair)
        
        required_price    = entry_price + (entry_price*DCA_.TARGET_PROFIT_PERCENT/100)
        required_price    = self.round_decimals_down(required_price, self.__get_max_price_prec(symbol_pair))
        sell_order_result = self.limit_order(Trade.SELL, quantity, symbol_pair, required_price)
        
        if self.has_result(sell_order_result):
            profit_potential = entry_price * quantity * DCA_.TARGET_PROFIT_PERCENT/100
            G.log_file.print_and_log(f"sell: limit order placed {symbol_pair} {sell_order_result[Dicts.RESULT][Dicts.DESCR][Dicts.ORDER]}, Profit Potential: ${profit_potential}")

            sell_order_txid = sell_order_result[Dicts.RESULT][Data.TXID][0]
            
            sql = SQL()
            sql.create_db_connection()
            query = f"INSERT INTO open_sell_orders {sql.oso_columns} VALUES ('{symbol_pair}', '{symbol}', {profit_potential}, false, false, '{sell_order_txid}')"
            sql.update(query)
            sql.close_db_connection()
        else:
            G.log_file.print_and_log(f"place_sell_limit_base_order: {symbol_pair} {sell_order_result[Dicts.ERROR]}")

        return sell_order_result
    
##################################################################
### Run the entire sell process for safety orders
##################################################################
    def start(self, symbol_pair: str, symbol: str, filled_buy_order_txid: str) -> None:
        """
        Everytime an open_buy_order is filled we need to
            1. Set filled=true in open_buy_orders table
            2. Cancel the open_sell_order on 'symbol_pair'
            3. Place a new sell order
            4. insert new sell order into open_sell_order table

        """
        sql = SQL()
        
        sql.con_update_set(SQLTable.OPEN_BUY_ORDERS, "filled=true", f"WHERE symbol_pair='{symbol_pair}' AND obo_txid='{filled_buy_order_txid}' AND filled=false")
        
        # get profit from open_buy_orders table
        result_set = sql.con_get_profit("open_buy_orders", f"WHERE obo_txid='{filled_buy_order_txid}'")
        profit_potential = result_set.fetchone()[0] if result_set.rowcount > 0 else 0
        
        # 2. cancel open_sell_order
        self.__cancel_open_sell_order(symbol_pair)

        # 3. change cancelled sell order to true in open_sell_orders
        sql.con_update_set(SQLTable.OPEN_SELL_ORDERS, "cancelled=true", f"symbol_pair='{symbol_pair}' AND filled=false LIMIT 1")
        
        sell_order_result = self.__place_sell_limit_order(symbol_pair, filled_buy_order_txid)
        sell_order_txid   = self.__get_sell_order_txid(sell_order_result)
        
        # insert sell order into sql
        sql.con_insert(f"INSERT INTO open_sell_orders {sql.oso_columns} VALUES ('{symbol_pair}', '{symbol}', {sell_order_txid}, {profit_potential}, false, false, '{sell_order_txid}')")

        

        # update open_buy_orders table
        sql.con_update_set(SQLTable.OPEN_BUY_ORDERS, "filled=true", f"obo_txid='{filled_buy_order_txid}' AND filled=false")
        
        
        return