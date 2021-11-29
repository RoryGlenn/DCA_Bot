
"""sell.py: Sells coin on kraken exchange based on users config file."""

from pprint                              import pprint
from bot_features.dca                    import DCA
from bot_features.low_level.kraken_enums import *
from util.globals                        import G
from bot_features.low_level.kraken_base  import KrakenBase
from my_sql.sql                          import SQL
from bot_features.colors                 import Color


class Sell(KrakenBase):
    def __init__(self, parameter_dict: dict) -> None:
        super().__init__(parameter_dict)
        self.asset_pairs_dict:  dict = self.get_all_tradable_asset_pairs()[Dicts.RESULT]
        self.sell_order_placed: bool = False
        self.dca:               DCA  = None

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

    def __get_sell_order_txid(self, sell_order_result) -> str:
        if not self.has_result(sell_order_result):
            raise Exception(f"sell.__get_sell_order_txid: {sell_order_result}")        
        return sell_order_result[Dicts.RESULT][Data.TXID][0]

    def __cancel_open_sell_order(self, symbol_pair: str) -> None:
        """
        Cancel the open sell order based on txid stored in the open_sell_orders table.
        Set cancelled=true in open_sell_orders table.

        """
        try:
            sql = SQL()
            
            result_set = sql.con_query(f"SELECT oso_txid FROM open_sell_orders WHERE symbol_pair='{symbol_pair}' AND cancelled=false AND filled=false")
            
            if result_set.rowcount > 0:
                for oso_txid in result_set.fetchall():
                    self.cancel_order(oso_txid[0])
                    sql.con_update(f"UPDATE open_sell_orders SET cancelled=true WHERE symbol_pair='{symbol_pair}' AND cancelled=false AND filled=false and oso_txid='{oso_txid[0]}'")
                    
                    row = sql.con_query(f"SELECT * FROM open_sell_orders WHERE symbol_pair='{symbol_pair}' AND cancelled=true AND filled=false and oso_txid='{oso_txid[0]}'")
                    
                    if row.rowcount > 0:
                        row = row.fetchall()[0]
                        G.log_file.print_and_log(Color.BG_GREY + f"Cancelled Sell order {row[2]} {Color.ENDC} {row[0]}")
        except Exception as e:
            G.log_file.print_and_log(e=e, error_type=type(e).__name__, filename=__file__, tb_lineno=e.__traceback__.tb_lineno)
        return

    
    def __place_sell_limit_order(self, symbol_pair: str, filled_buy_order_txid: str) -> dict:
        """
        Place limit order to sell the coin.
        
        """
        try:
            sql = SQL()

            result_set      = sql.con_query(f"SELECT MIN(safety_order_no) FROM open_buy_orders WHERE symbol_pair='{symbol_pair}' AND filled=false")
            safety_order_no = sql.parse_so_number(result_set)
            row             = sql.con_get_row(SQLTable.SAFETY_ORDERS, symbol_pair, safety_order_no)

            nonrounded_req_price = row[7]
            max_prec             = self.get_max_price_precision(symbol_pair)
            required_price       = self.round_decimals_down(nonrounded_req_price, max_prec)
            max_prec             = self.get_max_volume_precision(symbol_pair)
            qty_to_sell          = self.round_decimals_down(row[5], max_prec)
            sell_order_result    = self.limit_order(Trade.SELL, qty_to_sell, symbol_pair, required_price)
            
            if self.has_result(sell_order_result):
                result_set       = sql.con_query(f"SELECT profit FROM open_buy_orders WHERE symbol_pair='{symbol_pair}' AND obo_txid='{filled_buy_order_txid}'")
                profit_potential = round(result_set.fetchone()[0] if result_set.rowcount > 0 else 0, 6)
                G.log_file.print_and_log(Color.BG_BLUE + f"Sell limit order placed{Color.ENDC} {symbol_pair} {sell_order_result[Dicts.RESULT][Dicts.DESCR][Dicts.ORDER]}, Profit Potential: ${profit_potential}")
            else:
                G.log_file.print_and_log(Color.FG_YELLOW + f"Sell: {Color.ENDC} {symbol_pair} {sell_order_result[Dicts.ERROR]}" )
            return sell_order_result
        except Exception as e:
            G.log_file.print_and_log(e=e, error_type=type(e).__name__, filename=__file__, tb_lineno=e.__traceback__.tb_lineno)
        return

##################################################################
### Place sell order for base order only!
##################################################################
    def place_sell_limit_base_order(self, symbol_pair: str, entry_price: float, quantity: float) -> dict:
        """Create a sell limit order for the base order only!"""
        sql = SQL()
        
        # cancel open sell order based on what is inside the database column
        self.__cancel_open_sell_order(symbol_pair)
        
        required_price    = entry_price + (entry_price*DCA_.TARGET_PROFIT_PERCENT/100)
        required_price    = self.round_decimals_down(required_price, self.get_max_price_precision(symbol_pair))
        sell_order_result = self.limit_order(Trade.SELL, quantity, symbol_pair, required_price)

        if self.has_result(sell_order_result):
            profit_potential = round(entry_price * quantity * DCA_.TARGET_PROFIT_PERCENT/100, 6)
            G.log_file.print_and_log(Color.BG_BLUE + f"Sell limit order placed{Color.ENDC} {symbol_pair} {sell_order_result[Dicts.RESULT][Dicts.DESCR][Dicts.ORDER]}, Profit Potential: ${profit_potential}" + Color.ENDC)
            sell_order_txid = sell_order_result[Dicts.RESULT][Data.TXID][0]

            # get the values from the safety order in order to place it into open_sell_orders table
            row = sql.con_get_row(SQLTable.SAFETY_ORDERS, symbol_pair, 1)
            
            sql.con_update(f"""INSERT INTO open_sell_orders {sql.oso_columns} VALUES 
                           ('{row[0]}', '{row[1]}', {row[2]},   {row[3]},
                             {row[4]},   {row[5]},  {row[6]},   {row[7]},
                             {row[8]},   {row[9]},  {row[10]},  {row[11]},
                             {row[12]},  false,     false,     '{sell_order_txid}',
                             {row[14]}
                            )""")
        else:
            G.log_file.print_and_log(f"place_sell_limit_base_order: {symbol_pair} {sell_order_result[Dicts.ERROR]}")
        return sell_order_result
    
    
##################################################################
### Run the entire sell process for safety orders
##################################################################
    def start(self, symbol_pair: str, filled_buy_order_txid: str) -> None:
        """
        Everytime an open_buy_order is filled we need to
            1. Cancel the open_sell_order on 'symbol_pair'
            2. Place a new sell order
            3. insert new sell order into open_sell_order table

        """
        try:
            sql = SQL()
            
            self.__cancel_open_sell_order(symbol_pair) # ERROR: || list index out of range, IndexError C:\Users\Rory Glenn\Documents\python_repos\Kraken\DCA_Bot\src\bot_features\sell.py 131

            sell_order_result = self.__place_sell_limit_order(symbol_pair, filled_buy_order_txid)
            sell_order_txid   = self.__get_sell_order_txid(sell_order_result)
            result_set        = sql.con_query(f"SELECT MIN(safety_order_no) FROM {SQLTable.OPEN_BUY_ORDERS} WHERE symbol_pair='{symbol_pair}' AND filled=false")
            
            if result_set.rowcount > 0:
                safety_order_number = sql.parse_so_number(result_set)
                row                 = sql.con_get_row(SQLTable.OPEN_BUY_ORDERS, symbol_pair, safety_order_number)
                
                # insert sell order into sql
                sql.con_update(f"""INSERT INTO open_sell_orders {sql.oso_columns} VALUES 
                              ('{row[0]}', '{row[1]}', {row[2]},   {row[3]},
                                {row[4]},   {row[5]},  {row[6]},   {row[7]},
                                {row[8]},   {row[9]},  {row[10]},  {row[11]},
                                {row[12]},  false,     false,     '{sell_order_txid}',
                                {row[15]}
                            )""")
        except Exception as e:
            G.log_file.print_and_log(e=e, error_type=type(e).__name__, filename=__file__, tb_lineno=e.__traceback__.tb_lineno)
        return
