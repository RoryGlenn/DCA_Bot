import mysql.connector
from mysql.connector.cursor import MySQLCursorBuffered
from mysql.connector.cursor_cext     import CMySQLCursor
from mysql.connector.connection_cext import CMySQLConnection

class SQL():
    def __init__(self, host_name: str = "localhost", user_name: str = "root", user_password: str = "12345", db_name: str = "dca") -> None:
        self.host_name:     str              = host_name
        self.user_name:     str              = user_name
        self.user_password: str              = user_password
        self.db_name:       str              = db_name
        self.so_columns:    str              = "(symbol_pair, safety_order_no, deviation, quantity, total_quantity, price, average_price, required_price, required_change, profit, order_placed, so_key)"
        self.obo_columns:   str              = "(symbol_pair, txid, required_price, profit, filled, bo_key)"
        self.connection:    CMySQLConnection = None
        return

    def create_db_connection(self) -> None:
        try:
            self.connection = mysql.connector.connect(
                host=self.host_name,
                user=self.user_name,
                passwd=self.user_password,
                database=self.db_name)
            print("MySQL Database connection successful")
        except Exception as e:
            print(e)
        return 
    
    def close_db_connection(self) -> None:
        try:
            if self.connection is not None:
                cursor: CMySQLCursor = self.connection.cursor()
                cursor.close()
                self.connection.close()
                print("MySQL Database connection closed")
            else:
                print("MySQL no connection open")
        except Exception as e:
            print(e)
        return

    def execute_update(self, query: str):
        try:
            cursor: CMySQLCursor = self.connection.cursor()
            cursor.execute(query)
            self.connection.commit()
            print("Update was successful")
        except Exception as e:
            print(e)
        return cursor

    def execute_query(self, query: str):
        try:
            cursor: MySQLCursorBuffered = self.connection.cursor(buffered=True)
            cursor.execute(query)
            # self.connection.fetchall()
            print("Query was successful")
        except Exception as e:
            print(e)
        return cursor

    def create_tables(self):
        """Drops and creates the tables."""
        
        safety_orders = """
            CREATE TABLE safety_orders (
                symbol_pair         VARCHAR(20) NOT NULL,
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
                txid           VARCHAR(30) NOT NULL UNIQUE,
                required_price FLOAT       NOT NULL,
                profit         FLOAT       NOT NULL,
                filled         BOOLEAN     NOT NULL,
                bo_key         INT         NOT NULL,

                PRIMARY KEY (bo_key),
                FOREIGN KEY (bo_key) REFERENCES safety_orders(so_key)
            );  """

        open_sell_orders = """
            CREATE TABLE open_sell_orders (
                symbol_pair VARCHAR(20) NOT NULL,
                txid        VARCHAR(30) PRIMARY KEY,
                profit      FLOAT       NOT NULL,
                filled      BOOLEAN     NOT NULL,
                oso_key     INT         NOT NULL,
                FOREIGN KEY (oso_key) REFERENCES open_buy_orders(bo_key)
            );  """

        self.execute_update("DROP TABLE open_sell_orders")
        self.execute_update("DROP TABLE open_buy_orders")
        self.execute_update("DROP TABLE safety_orders")
        self.execute_update(safety_orders)
        self.execute_update(open_buy_orders)
        self.execute_update(open_sell_orders)        
        return

    def insert(self, table_name):
        query = f'INSERT INTO {table_name} \
            (symbol_pair, safety_order_no, deviation, quantity, total_quantity, price, average_price, required_price, required_change, profit, order_placed, so_key) \
                VALUES ("SOLUSD", 1, 1.3, 0.2, 0.4, 234.86652, 234.86652, 237.2151852, 0.99009901, 0.93946608, False, so_key)'
        self.execute_update(query)
        return
