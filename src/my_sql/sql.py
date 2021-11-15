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
        self.oso_columns:   str              = "(symbol_pair, profit, filled, oso_txid)"
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


    def drop_all_tables(self):
        self.execute_update("DROP TABLE open_sell_orders")
        self.execute_update("DROP TABLE open_buy_orders")
        self.execute_update("DROP TABLE safety_orders")
        return

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
                txid                VARCHAR(30),  -- new
                so_key              INT         NOT NULL AUTO_INCREMENT,
                PRIMARY KEY (so_key)
            );  """

        open_buy_orders = """
            CREATE TABLE open_buy_orders (
                symbol_pair    VARCHAR(20) NOT NULL,
                required_price FLOAT       NOT NULL,
                profit         FLOAT       NOT NULL,
                filled         BOOLEAN     NOT NULL,

                obo_txid           VARCHAR(30) PRIMARY KEY -- new
            );  """

        open_sell_orders = """
            CREATE TABLE open_sell_orders (
                symbol_pair VARCHAR(20) NOT NULL,
                profit      FLOAT       NOT NULL,
                filled      BOOLEAN     NOT NULL,
                oso_txid    VARCHAR(30) PRIMARY KEY -- new
            );  """

        self.execute_update(safety_orders)
        self.execute_update(open_buy_orders)
        self.execute_update(open_sell_orders)        
        return

    def insert_dummy_data(self):
        query = list()
        query.append(f"INSERT INTO safety_orders {self.so_columns} VALUES ('OXTUSD',	1,	1.3,     10,        20,	        0.696358,	0.696358,	0.703322,	0.990099, 0.139272,	false,	1)")
        query.append(f"INSERT INTO safety_orders {self.so_columns} VALUES ('OXTUSD',	2,	3.328,   25,        35,	        0.68205,	0.689204,	0.696096,	2.01784,  0.306922,	false,	2)")
        query.append(f"INSERT INTO safety_orders {self.so_columns} VALUES ('OXTUSD',	3,	6.49168, 62.5,      87.5,	    0.659729,	0.674467,	0.681211,	3.15351,  0.709209,	false,	3)")
        query.append(f"INSERT INTO safety_orders {self.so_columns} VALUES ('OXTUSD',	4,	11.427,  156.25,    218.75,	    0.624909,	0.649688,	0.656185,	4.7663,   1.6482,   false,	4)")
        query.append(f"INSERT INTO safety_orders {self.so_columns} VALUES ('OXTUSD',	5,	19.1262, 390.625, 	546.875,    0.570589,	0.610139,	0.61624,    7.40794,  3.73379,	false,	5)")
        query.append(f"INSERT INTO safety_orders {self.so_columns} VALUES ('OXTUSD',	6,	31.1368, 976.562, 	1367.19,    0.485851,	0.547995,	0.553474,	12.2181,  7.92392,	false,	6)")
        query.append(f"INSERT INTO safety_orders {self.so_columns} VALUES ('OXTUSD',	7,	49.8734, 2441.41, 	3417.97,    0.353658,	0.450826,	0.455335,	22.33,    14.4022,	false,	7)")

        for q in query:
            self.execute_update(q)
        return
