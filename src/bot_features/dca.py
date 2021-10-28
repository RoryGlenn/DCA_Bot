"""dca.py - DCA is a dollar cost averaging technique. 
This bot uses DCA in order lower the average buy price for a purchased coin."""

import os
import pandas as pd

from pprint                    import pprint
from kraken_files.kraken_enums import *
from util.globals              import G

class DCA(DCA_):
    def __init__(self, symbol: str, order_min: float, bid_price: float):
        self.percentage_deviation_levels:       list         = list()
        self.price_levels:                      list         = list()
        self.quantities:                        list         = list()
        self.average_price_levels:              list         = list()
        self.required_price_levels:             list         = list()
        self.required_change_percentage_levels: list         = list()
        self.symbol:                            str          = symbol
        self.excel_directory:                   str          = EXCEL_FILES_DIRECTORY
        self.file_path:                         str          = EXCEL_FILES_DIRECTORY + "/" + self.symbol + ".xlsx"
        self.bid_price:                         float        = bid_price
        self.base_order_quantity_to_buy:        float        = 0.0
        self.safety_order_quantity_to_buy:      float        = 0.0
        self.order_min:                         float        = order_min
        self.safety_orders:                     dict         = { }
        self.account_balance:                   dict         = { }
        self.trade_history:                     dict         = { }
        self.safety_order_table:                pd.DataFrame = pd.DataFrame()
        self.base_order_table:                  pd.DataFrame = pd.DataFrame()
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
            self.__reinterpret_order_size()
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
            if not os.path.exists(self.excel_directory):
                os.mkdir(self.excel_directory)
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

        # for base order
        self.percentage_deviation_levels.append(0)

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

        # base order
        self.price_levels.append(self.bid_price)

        # safety orders
        for i in range(BASE_ORDER, DCA_.SAFETY_ORDERS_MAX+1):
            level = self.percentage_deviation_levels[i] / 100
            price = self.bid_price - (self.bid_price * level)
            self.price_levels.append(price)
        return

    def __reinterpret_order_size(self) -> None:
        """Converts the usd base_order_size and safety_order_size into the quantity of coin we can buy."""
        self.base_order_quantity_to_buy   = self.order_min #DCA_.BASE_ORDER_SIZE   / self.bid_price
        self.safety_order_quantity_to_buy = self.order_min #DCA_.SAFETY_ORDER_SIZE / self.bid_price
        return

    def __set_quantity_levels(self) -> None:
        """Sets the quantity to buy for each safety order number."""
        prev = self.safety_order_quantity_to_buy
        
        # base order
        self.quantities.append(self.base_order_quantity_to_buy)

        # first safety order
        self.quantities.append(self.safety_order_quantity_to_buy)

        # remaining safety orders
        for _ in range(BASE_ORDER, DCA_.SAFETY_ORDERS_MAX):
            self.quantities.append(DCA_.SAFETY_ORDER_VOLUME_SCALE * prev)
            prev = DCA_.SAFETY_ORDER_VOLUME_SCALE * prev
        return
    
    def __set_average_price_levels(self) -> None:
        """Sets the average price level for each safety order number."""
        prev_average = self.price_levels[0]

        # base order
        self.average_price_levels.append(self.price_levels[0])

        # safety orders
        for i in range(BASE_ORDER, DCA_.SAFETY_ORDERS_MAX+1):
            average = (self.price_levels[i] + prev_average) / 2
            self.average_price_levels.append(average)
            prev_average = average
        return

    def __set_required_price_levels(self) -> None:
        """Sets the required price for each safety order number."""
        target_profit_decimal = DCA_.TARGET_PROFIT_PERCENT / 100

        # base order
        base_order_price = self.bid_price + (self.bid_price*target_profit_decimal)
        self.required_price_levels.append(base_order_price)

        # safety orders
        for i in range(BASE_ORDER, DCA_.SAFETY_ORDERS_MAX+1):
            required_price = self.average_price_levels[i] + (self.average_price_levels[i] * target_profit_decimal)
            self.required_price_levels.append(required_price)
        return

    def __set_required_change_percentage_levels(self) -> None:
        """Sets the required change percent for each safety order number."""
        # base order
        self.required_change_percentage_levels.append(DCA_.TARGET_PROFIT_PERCENT)

        # safety orders
        for i in range(BASE_ORDER, DCA_.SAFETY_ORDERS_MAX+1):
            required_change_percentage = (1 - (self.price_levels[i] / self.required_price_levels[i])) * 100
            self.required_change_percentage_levels.append(required_change_percentage)
        return

    def __load_safety_order_table(self) -> None:
        """Uses a DataFrame to load the .xlsx file associated with the symbol into memory."""
        self.safety_order_table = pd.read_excel(self.file_path, SheetNames.SAFETY_ORDERS)
        return

    def __set_safety_order_table(self) -> None:
        """Set the Dataframe with the values calculated in previous functions."""
        order_numbers = [i for i in range(DCA_.SAFETY_ORDERS_MAX+1)]

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
        """Read the first line in the .xlsx file into memory, then delete it."""
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
        