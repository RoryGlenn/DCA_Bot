"""spot.py: Supports base functionality for buying, selling and transfering. Meant to be inherited from for additional classes"""

import ast
from datetime import datetime
from pprint import pprint

import pandas as pd
import requests
from kraken_files.kraken_api import KrakenAPI
from kraken_files.kraken_enums import *
from util.globals import G



class Base(KrakenAPI):
    def __init__(self, parameter_dict: dict) -> None:
        """
        Returns new Spot object with specified data
        
        """
        super().__init__(key=parameter_dict[KRAKEN_API_KEY],
                         secret=parameter_dict[KRAKEN_SECRET_KEY])
        self.asset_pairs_dict:   dict = {}
        # self.kraken_assets_dict: dict = {}
        return
       
    def get_current_time(self) -> str:
        """Returns the current time in hours:minutes:seconds format."""
        return datetime.now().strftime("%H:%M:%S")

    def wait(self, message: str = "", timeout: int = Nap.NORMAL) -> bool:
        """
        Sleep function that also checks if the global exit event has been triggered.
        
        """
        if message != "":
            G.log_file.print_and_log(message)

        # timeout in number of seconds
        if not G.thread_exit_event.wait(timeout):
            return True
        return False


    def get_all_tradable_asset_pairs(self) -> dict:
        """
        Returns a dictionary containing all legal trading pairs on kraken
        For example, if you want to trade XLTC/USD, search the keys
        of the returned dictionary for the symbol pair. If the pair is
        not in the dictionary, the pair cannot be used to buy or sell.
        
        """
        response = requests.get(URL_ASSET_PAIRS)
        return ast.literal_eval(response.text)
            
    def get_order_min(self, symbol: str) -> float:  
        """
        Returns the min quantity of coin we can order per USD.
        
        """

        pair = self.get_tradable_asset_pair(symbol)
        return float(self.asset_pairs_dict[pair][Dicts.ORDER_MIN])
    
    def get_max_price_precision(self, symbol: str) -> int:
        """
        Returns the maximum price precision in number of decimals
        
        """

        pair = self.get_tradable_asset_pair(symbol)
        return int(self.asset_pairs_dict[pair][Dicts.PAIR_DECIMALS])

    def get_max_volume_precision(self, symbol: str) -> int:
        """
        Returns the maximum volume precision in terms number of decimals
        
        """
        pair = self.get_tradable_asset_pair(symbol)
        return int(self.asset_pairs_dict[pair][Dicts.LOT_DECIMALS])
        
    def get_withdrawal_precision_max(self, symbol: str) -> int:
        """Gets maximum decimal places when withdrawal of coin"""
        return int(self.get_asset_info()[Dicts.RESULT][symbol][Dicts.DECIMALS])
        

    def get_roi_percent(self, current_value: float, entry_value: float) -> float:
        """
        Calculate the return on investment (roi) of the symbols current_value and entry_value.
        Then convert from percent to decimal by multiplying by 100.
        
        """
        
        return ((current_value / entry_value) - 1) * 100


    def get_ask_price(self, symbol_pair: str) -> float:
        """
        Gets the current ask price for a symbol pair on kraken. 
        
        """
        
        current_price = self.get_ticker_information(pair=symbol_pair)
        current_price = self.parse_ticker_information(current_price)
        return self.parse_ask_price(current_price)

    def get_bid_price(self, symbol_pair: str) -> float:
        """Gets the current bid price for a symbol pair"""
        current_price = self.get_ticker_information(pair=symbol_pair)
        current_price = self.parse_ticker_information(current_price)
        return self.parse_bid_price(current_price)

    def get_alt_name(self, symbol: str) -> str:
        assets = self.get_asset_info()
        return assets[Dicts.RESULT][symbol][Dicts.ALT_NAME]

    def get_tradable_asset_pair(self, symbol: str) -> str:
        """Returns the asset pair that matches the symbol and can be traded with either USD or ZUSD."""
        while len(symbol) > 0:
            if symbol + StableCoins.USD in self.asset_pairs_dict.keys():
                return symbol + StableCoins.USD
            elif symbol + StableCoins.ZUSD in self.asset_pairs_dict.keys():
                return symbol + StableCoins.ZUSD
            else:
                """
                If we couldn't find the symbol pair, try removing the first character in the symbol and search again
                This will probably happen with symbols like "XXDG"
                
                """
                symbol = symbol[1:]
        return "NOT FOUND"

    def get_pair_decimals(self, symbol_pair: str) -> int:
        """Returns pair_decimals: this is the maximum amount of decimals you can use to order the coin in terms of USD.
        For example, if you want to order 1 FILUSD, the max decimals you can use for price will be determined by the pair_decimals key.
        If pair_decimals is 3, then 60.111 will be the most specific price you can use.
        If pair_decimals is 4, then 60.1111 will be the most specific price you can use."""
        return self.asset_pairs_dict[symbol_pair][Dicts.PAIR_DECIMALS]

    def has_result(self, dictionary: dict) -> bool:
        """Returns True if "result" is returned in dict.
        If "result" not in dict, an error occurred."""
        return bool(Dicts.RESULT in dictionary.keys())

    def print_order_result(self, symbol: str, order_result: dict) -> None:
        if self.has_result(order_result):
            G.log_file.print_and_log(f"sell_loop: limit order {symbol}: {order_result}", money=True)
        else:
            G.log_file.print_and_log(f"sell_loop: did not sell {symbol} {order_result}", money=True)        
        return

    def get_withdrawal_minimum(self, symbol: str) -> float:
        """
        Gets the minimum withdrawal quantity for any coin on kraken

        """

        df = pd.read_csv(KrakenFiles.WITHDRAWAL_MINIMUMS)
        for _, row in df.iterrows():
            if row[Dicts.ASSET] == symbol:
                return row[Dicts.MINIMUM]

        """
        If we couldn't find the first symbol, search again without the first character
        We have to do this with symbols like XXLM, or XLTC"""
        return self.get_withdrawal_minimum(symbol[1:])

    def get_quantity_owned(self, symbol: str) -> float:
        account_balance = self.get_account_balance()
        for sym, value in account_balance.items():
            if sym == symbol:
                return float(value)
        return 0

    def convert_quantities(self, coin1_qty: float, coin2_ask_price: float) -> float:
        """Get the value of coin1 in terms of coin2.
        
        For example If we have 100 USD and we want to 
        buy Bitcoin when it is valued at 50,000 dollars for 1, return 0.002 BTC

        """
        coin2_quantity = coin1_qty / coin2_ask_price
        return coin2_quantity


    def get_decimal_places(self, number: float) -> int:
        """Returns the number of decimal places after the period in a floating point number.
        For example: 
            6 = get_decimal_places(12.234829)
        """
        number:              str = str(number)
        decimal_place_index: int = number.find(".")
        return len(number[decimal_place_index:])
        

    def get_minimum_value(self, price: float, symbol: str) -> float:
        return price * self.get_order_min(symbol)
