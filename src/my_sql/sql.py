import mysql.connector

from mysql.connector.connection_cext import CMySQLConnection
from mysql.connector.cursor          import MySQLCursorBuffered
from mysql.connector.cursor_cext     import CMySQLCursor


class SQL():
    def __init__(self, host_name: str = "localhost", user_name: str = "root", user_password: str = "12345", db_name: str = "dca") -> None:
        self.host_name:     str              = host_name
        self.user_name:     str              = user_name
        self.user_password: str              = user_password
        self.db_name:       str              = db_name
        self.so_columns:    str              = "(symbol_pair, symbol, safety_order_no, deviation, quantity, total_quantity, price, average_price, required_price, required_change, profit, order_placed, so_key)"
        self.obo_columns:   str              = "(symbol_pair, symbol, required_price, profit, filled, obo_txid)"
        self.oso_columns:   str              = "(symbol_pair, symbol, profit, cancelled, filled, oso_txid)"
        self.connection:    CMySQLConnection = None
        return

    def create_db_connection(self) -> None:
        try:
            self.connection = mysql.connector.connect(
                host=self.host_name,
                user=self.user_name,
                passwd=self.user_password,
                database=self.db_name)
        except Exception as e:
            print(e)
        return 
    
    def close_db_connection(self) -> None:
        try:
            if self.connection is not None:
                cursor: CMySQLCursor = self.connection.cursor()
                cursor.close()
                self.connection.close()
            else:
                print("MySQL no connection open")
        except Exception as e:
            print(e)
        return

    def update(self, query: str) -> CMySQLCursor:
        try:
            cursor: CMySQLCursor = self.connection.cursor()
            cursor.execute(query)
            self.connection.commit()
        except Exception as e:
            print(e)
        return cursor

    def query(self, query: str) -> MySQLCursorBuffered:
        try:
            cursor: MySQLCursorBuffered = self.connection.cursor(buffered=True)
            cursor.execute(query)
        except Exception as e:
            print(e)
        return cursor
    
    def con_query(self, query: str) -> MySQLCursorBuffered:
        try:
            self.create_db_connection()
            cursor: MySQLCursorBuffered = self.connection.cursor(buffered=True)
            cursor.execute(query)
        except Exception as e:
            print(e)
        
        cursor.close()
        self.close_db_connection()
        return cursor    
    
    def con_update(self, query: str):
        self.create_db_connection()
        result_set = self.update(query)
        result_set.close()
        self.close_db_connection()
        return
    
    def con_update_set(self, table_name: str, cond1: str, cond2: str) -> None:
        self.create_db_connection()
        cursor = self.update(f"UPDATE {table_name} SET {cond1} WHERE {cond2}")
        cursor.close()
        self.close_db_connection()
        return
    
    def con_insert(self, stmt: str) -> None:
        self.create_db_connection()
        cursor = self.update(stmt)
        cursor.close()
        self.close_db_connection()
        return
    
    def con_delete(self, tablename: str, symbol_pair: str) -> None:
        """Deletes row data from tablename given symbol_pair"""
        self.create_db_connection()
        result_set = self.update(f"DELETE FROM {tablename} WHERE symbol_pair='{symbol_pair}'")
        result_set.close()
        self.close_db_connection()
        return

    def drop_all_tables(self) -> None:
        self.update("DROP TABLE open_sell_orders")
        self.update("DROP TABLE open_buy_orders")
        self.update("DROP TABLE safety_orders")
        return

    def create_tables(self) -> None:
        """Drops and creates the tables."""
        
        safety_orders = """
            CREATE TABLE safety_orders (
                symbol_pair         VARCHAR(20) NOT NULL,
                symbol              VARCHAR(10) NOT NULL,
                safety_order_no     INT         NOT NULL,
                deviation           FLOAT       NOT NULL,
                quantity            FLOAT       NOT NULL,
                total_quantity      FLOAT       NOT NULL,
                price               FLOAT       NOT NULL,
                average_price       FLOAT       NOT NULL, 
                required_price      FLOAT       NOT NULL,
                required_change     FLOAT       NOT NULL,
                profit              FLOAT       NOT NULL,
                order_placed        BOOLEAN     NOT NULL,
                so_key              INT         NOT NULL AUTO_INCREMENT,
                PRIMARY KEY (so_key)
            );  """

        open_buy_orders = """
            CREATE TABLE open_buy_orders (
                symbol_pair    VARCHAR(20) NOT NULL,
                symbol         VARCHAR(10) NOT NULL,
                required_price FLOAT       NOT NULL,
                profit         FLOAT       NOT NULL,
                filled         BOOLEAN     NOT NULL,
                obo_txid       VARCHAR(30) PRIMARY KEY
            );  """

        open_sell_orders = """
            CREATE TABLE open_sell_orders (
                symbol_pair VARCHAR(20) NOT NULL,
                symbol      VARCHAR(10) NOT NULL,
                profit      FLOAT       NOT NULL,
                cancelled   BOOLEAN     NOT NULL,
                filled      BOOLEAN     NOT NULL,
                oso_txid    VARCHAR(30) PRIMARY KEY
            );  """

        self.update(safety_orders)
        self.update(open_buy_orders)
        self.update(open_sell_orders)        
        return

    def con_get_symbols(self) -> set:
        bought_set = set()
        self.create_db_connection()
        result_set = self.query("SELECT symbol FROM safety_orders")
        result_set.close()
        self.close_db_connection()
        for symbol in result_set.fetchall():
            bought_set.add(symbol[0])
        return bought_set
    
    def con_get_symbol_pairs(self) -> set:
        """Gets the symbol pairs that are currently in the database under the safety_orders table."""
        bought_set = set()
        self.create_db_connection()
        result_set = self.query("SELECT symbol_pair FROM safety_orders")
        result_set.close()
        self.close_db_connection()
        for symbol in result_set.fetchall():
            bought_set.add(symbol[0])
        return bought_set
    
    def con_get_profit(self, table_name: str, conditions: str) -> MySQLCursorBuffered:
        self.create_db_connection()
        result_set = self.query(f"SELECT profit FROM {table_name} {conditions}")
        result_set.close()
        self.close_db_connection()
        return result_set
        
    def con_get_required_price(self, table_name: str, symbol_pair: str) -> float:
        self.create_db_connection()
        result_set = self.query(f"SELECT required_price FROM {table_name} WHERE symbol_pair='{symbol_pair}' AND order_placed=false LIMIT 1")
        result_set.close()
        self.close_db_connection()
        req_price_list = result_set.fetchall()
        return req_price_list[0][0] if result_set.rowcount > 0 else -1
    
    def con_get_open_buy_orders(self, symbol_pair: str) -> int:
        self.create_db_connection()
        result_set = self.query(f"SELECT symbol_pair FROM open_buy_orders WHERE symbol_pair='{symbol_pair}' AND filled=false")
        result_set.close()
        self.close_db_connection()
        return len(result_set.fetchall())
        
    def con_get_quantities(self, symbol_pair: str) -> list:
        self.create_db_connection()
        result_set = self.query(f"SELECT quantity FROM safety_orders WHERE symbol_pair='{symbol_pair}' AND order_placed=false")
        result_set.close()
        self.close_db_connection()
        return [quantity[0] for quantity in result_set.fetchall()] if result_set.rowcount > 0 else []
    
    def con_get_prices(self, symbol_pair: str) -> list:
        self.create_db_connection()
        result_set = self.query(f"SELECT price FROM safety_orders WHERE symbol_pair='{symbol_pair}' AND order_placed=false")
        result_set.close()
        self.close_db_connection()
        return [price[0] for price in result_set.fetchall()] if result_set.rowcount > 0 else []