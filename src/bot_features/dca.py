"""dca.py - DCA is a dollar cost averaging technique. 
This bot uses DCA in order lower the average buy price for a purchased coin."""

import os
import pandas as pd

from pprint                    import pprint
from kraken_files.kraken_enums import *
from util.globals              import G


class DCA(DCA_):
    def __init__(self, symbol: str, order_min: float, bid_price: float):
        self.percentage_deviation_levels:       list         = [ ]
        self.price_levels:                      list         = [ ]
        self.quantities:                        list         = [ ]
        self.average_price_levels:              list         = [ ]
        self.required_price_levels:             list         = [ ]
        self.required_change_percentage_levels: list         = [ ]
        self.symbol:                            str          = symbol
        self.file_path:                         str          = EXCEL_FILES_DIRECTORY + "/" + self.symbol + ".xlsx"
        self.bid_price:                         float        = bid_price
        self.order_min:                         float        = order_min
        self.safety_order_table:                pd.DataFrame = pd.DataFrame()
        self.safety_orders:                     dict         = { }
        self.account_balance:                   dict         = { }
        self.trade_history:                     dict         = { }
        self.__start()

    def __start(self) -> None:
        """Essentially the main function for DCA class.

        1. If the .xlsx file associated with the symbol passed in exists, the bot has previously
        put in at least DCA_.SAFETY_ORDERS_ACTIVE_MAX orders into the exchange. 
        The bot will continue to read from the .xlsx file until it runs out of safety orders.
        
        2. Once the bot runs out of safety orders, there is nothing left to do but to wait until the
        right time to sell the coin.

        3. If the sheet doesn't exist, the bot has not traded the coin and we should create a new one if the bot trades it.
        
        """
        self.__create_directory()

        """
        Need a way to sell the amount of coin from all the previous orders.
        This may include the quantity that we have no bought yet but is in an open order.
        """

        if not self.__has_safety_order_table():
            self.__set_deviation_percentage_levels()
            self.__set_price_levels()
            self.__set_quantity_levels()
            self.__set_average_price_levels()
            self.__set_required_price_levels()
            self.__set_required_change_percentage_levels()
            self.__set_safety_order_table()
            self.__create_excel_file()
        else:
            """if the safety order table exists for the symbol"""
            self.__load_safety_order_table()
        self.__set_buy_orders()
        return

    def __create_directory(self) -> None:
        """Create a directory for the safety orders."""
        try:
            if not os.path.exists(EXCEL_FILES_DIRECTORY):
                os.mkdir(EXCEL_FILES_DIRECTORY)
        except Exception as e:
            G.log_file.print_and_log(e=e)
        return

    def __has_safety_order_table(self) -> bool:
        """Returns True if the safety order excel file exists."""
        return os.path.exists(self.file_path)

    def __set_deviation_percentage_levels(self) -> None:
        """
        Safety order step scale:

        The scale will multiply step in percents between safety orders.
        Let's assume there is a bot with safety order price deviation 1% and the scale is 2. Safety order prices would be:

        It's the first order, we use deviation to place it: 0 + -1% = -1%.

        Last safety order step multiplied by the scale and then added to the last order percentage. The last step was 1%, the new step will be 1% * 2 = 2%. The order will be placed: -1% + -2% = -3%.

        Step 1: ...           Order 1: 0%  + 1%  = 1% (initial price deviation)
        Step 2: 1% * 2 = 2%.  Order 2: 1%  + 2%  = 3%.
        Step 3: 2% * 2 = 4%.  Order 3: 3%  + 4%  = 7%.
        Step 4: 4% * 2 = 8%.  Order 4: 7%  + 8%  = 15%.
        Step 5: 8% * 2 = 16%. Order 5: 15% + 16% = 31%.

        For more info: https://help.3commas.io/en/articles/3108940-main-settings
        """     
        
        # for first safety order
        self.percentage_deviation_levels.append(round(DCA_.SAFETY_ORDER_PRICE_DEVIATION, DECIMAL_MAX))

        # for second safety order
        step_percent = DCA_.SAFETY_ORDER_PRICE_DEVIATION * DCA_.SAFETY_ORDER_STEP_SCALE
        safety_order = DCA_.SAFETY_ORDER_PRICE_DEVIATION + step_percent
        self.percentage_deviation_levels.append(round(safety_order, DECIMAL_MAX))
        
        # for 3rd to DCA_.SAFETY_ORDERS_MAX
        for _ in range(2, DCA_.SAFETY_ORDERS_MAX):
            step_percent = step_percent * DCA_.SAFETY_ORDER_STEP_SCALE
            safety_order = safety_order + step_percent
            safety_order = round(safety_order, DECIMAL_MAX)
            self.percentage_deviation_levels.append(safety_order)
        return

    def __set_price_levels(self) -> None:
        """Save the coin prices levels in terms of USD into self.price_levels.
        Order 0: $34.4317911
        Order 1: $33.72431722
        Order n: ..."""

        # safety orders
        for i in range(DCA_.SAFETY_ORDERS_MAX):
            level = self.percentage_deviation_levels[i] / 100
            price = self.bid_price - (self.bid_price * level)

            if level == 0 or price == 0 or self.bid_price == 0 or self.percentage_deviation_levels[i] == 0:
                print(level)
                print(price)
                print(self.bid_price)
                print(self.percentage_deviation_levels[i])
                raise Exception("level, price, self.bid_price, self.percentage_deviation_levels[i] must not be 0")
            self.price_levels.append(price)
        return

    def __set_quantity_levels(self) -> None:
        """Sets the quantity to buy for each safety order number."""
        prev = self.order_min
        
        # first safety order
        self.quantities.append(self.order_min)

        # remaining safety orders
        for _ in range(1, DCA_.SAFETY_ORDERS_MAX):
            self.quantities.append(DCA_.SAFETY_ORDER_VOLUME_SCALE * prev)
            prev = DCA_.SAFETY_ORDER_VOLUME_SCALE * prev
        return
    
    def __set_average_price_levels(self) -> None:
        """Sets the average price level for each safety order number."""
        prev_average = self.price_levels[0]

        # safety orders
        for i in range(DCA_.SAFETY_ORDERS_MAX):
            average = (self.price_levels[i] + prev_average) / 2

            if average == 0:
                raise Exception("average must not be 0")
            self.average_price_levels.append(average)
            prev_average = average
        return

    def __set_required_price_levels(self) -> None:
        """Sets the required price for each safety order number."""
        target_profit_decimal = DCA_.TARGET_PROFIT_PERCENT / 100

        # safety orders
        for i in range(DCA_.SAFETY_ORDERS_MAX):
            required_price = self.average_price_levels[i] + (self.average_price_levels[i] * target_profit_decimal)

            if required_price == 0:
                raise Exception("required_price must not be 0")
            self.required_price_levels.append(required_price)
        return

    def __set_required_change_percentage_levels(self) -> None:
        """Sets the required change percent for each safety order number."""
        
        # safety orders
        for i in range(DCA_.SAFETY_ORDERS_MAX):
            try:
                required_change_percentage = (1 - (self.price_levels[i] / self.required_price_levels[i])) * 100
            except ZeroDivisionError as e:
                required_change_percentage = (1 - self.price_levels[i]) * 100
            except Exception as e:
                print(e)
            self.required_change_percentage_levels.append(required_change_percentage)
        return

    def __load_safety_order_table(self) -> None:
        """Uses a DataFrame to load the .xlsx file associated with the symbol into memory."""
        self.safety_order_table = pd.read_excel(self.file_path, SheetNames.SAFETY_ORDERS)
        return

    def __set_safety_order_table(self) -> None:
        """Set the Dataframe with the values calculated in previous functions."""
        order_numbers = [i for i in range(1, DCA_.SAFETY_ORDERS_MAX+1)]

        self.safety_order_table = pd.DataFrame({
                                    SOColumns.SAFETY_ORDER_NO: order_numbers,
                                    SOColumns.DEVIATION:       self.percentage_deviation_levels,
                                    SOColumns.QUANTITY:        self.quantities,
                                    SOColumns.PRICE:           self.price_levels,
                                    SOColumns.AVG_PRICE:       self.average_price_levels,
                                    SOColumns.REQ_PRICE:       self.required_price_levels,
                                    SOColumns.REQ_CHANGE_PERC: self.required_change_percentage_levels})
        return

    def __create_excel_file(self) -> None:
        with pd.ExcelWriter(self.file_path, engine=OPENPYXL, mode=FileMode.WRITE_TRUNCATE) as writer:
            # create the safety order table sheet
            self.safety_order_table.to_excel(writer, SheetNames.SAFETY_ORDERS, index=False)
            
            # create the open_orders sheet
            df1 = pd.DataFrame(data={OBOColumns.TXIDS: [], OBOColumns.REQ_PRICE: []})
            df1.to_excel(writer, SheetNames.OPEN_BUY_ORDERS, index=False)

            # create the sell_orders sheet
            df2 = pd.DataFrame(data={OSOColumns.TXIDS: []})
            df2.to_excel(writer, SheetNames.OPEN_SELL_ORDERS, index=False)
        return

    def __save_safety_order_table(self) -> None:
        """Writes self.safety_order_table to excel file"""
        df2 = pd.read_excel(self.file_path, SheetNames.OPEN_BUY_ORDERS)
        df3 = pd.read_excel(self.file_path, SheetNames.OPEN_SELL_ORDERS)

        with pd.ExcelWriter(self.file_path, engine=OPENPYXL, mode=FileMode.WRITE_TRUNCATE) as writer:
            self.safety_order_table.to_excel(writer, SheetNames.SAFETY_ORDERS, index=False)
            df2.to_excel(writer, SheetNames.OPEN_BUY_ORDERS, index=False)
            df3.to_excel(writer, SheetNames.OPEN_SELL_ORDERS, index=False)
        return

    def __set_buy_orders(self) -> None:
        """Read rows in the .xlsx file into memory."""
        safety_order_table = pd.read_excel(self.file_path)
        prices             = safety_order_table[SOColumns.PRICE].tolist()
        quantities         = safety_order_table[SOColumns.QUANTITY].tolist()

        if len(prices) < DCA_.SAFETY_ORDERS_ACTIVE_MAX:
            for i in range(len(prices)):
                self.safety_orders[i] = {prices[i]: quantities[i]}
        else:
            for i in range(DCA_.SAFETY_ORDERS_ACTIVE_MAX):
                self.safety_orders[i] = {prices[i]: quantities[i]}
        return

    def __remove_rows(self) -> None:
        """1. load the .xlsx file into a dataframe.
           2. drop the unnamed column.
           3. drop the safety order that we just put into the exchange. (this will always be the first row in the excel sheet)
           4. save the new table with the dropped rows."""
        safety_order_table = pd.read_excel(self.file_path, SheetNames.SAFETY_ORDERS)
        safety_order_table.drop(0, inplace=True)
        self.safety_order_table = safety_order_table
        return

    def update_safety_orders(self) -> None:
        """Rewrites the excel file with the dropped rows."""
        self.__remove_rows()
        self.__save_safety_order_table()
        return
        