"""tradingview.py - pulls data from tradingview.com to see which coins we should buy."""

import os

from tradingview_ta            import TA_Handler, Interval
from pprint                    import pprint
from kraken_files.kraken_enums import *
from util.globals              import G
from datetime                  import datetime

class TVData:
    SCREENER       = "crypto"
    EXCHANGE       = "kraken"
    RECOMMENDATION = "RECOMMENDATION"
    BUY            = "BUY"
    STRONG_BUY     = "STRONG_BUY"
    ALL_INTERVALS  = [
        Interval.INTERVAL_1_MINUTE, 
        Interval.INTERVAL_5_MINUTES, 
        Interval.INTERVAL_15_MINUTES, 
        Interval.INTERVAL_1_HOUR, 
        Interval.INTERVAL_2_HOUR,
        Interval.INTERVAL_4_HOURS,
        Interval.INTERVAL_1_DAY,
        Interval.INTERVAL_1_WEEK,
        Interval.INTERVAL_1_MONTH]
    SCALP_INTERVALS = [
        Interval.INTERVAL_1_MINUTE, 
        Interval.INTERVAL_5_MINUTES, 
        Interval.INTERVAL_15_MINUTES, 
        Interval.INTERVAL_1_HOUR, 
        Interval.INTERVAL_4_HOURS]


class TradingView():
    def __init__(self) -> None:
        pass
    
    def __get_recommendation(self, symbol_pair: str, interval: str) -> list:
        """Get a recommendation (buy or sell) for the symbol."""
        try:
            symbol_data = TA_Handler(symbol=symbol_pair, screener=TVData.SCREENER, exchange=TVData.EXCHANGE, interval=interval)
            return symbol_data.get_analysis().summary[TVData.RECOMMENDATION]
        except Exception as e:
            G.log_file.print_and_log(e=e, error_type=type(e).__name__, filename=__file__, tb_lineno=e.__traceback__.tb_lineno)
        return []

    def is_buy(self, symbol_pair: list) -> bool:
        """Get recommendations for all intervals in TVData. 
        Buy the coin if all intervals indicate a BUY or STRONG_BUY."""
        
        for interval in TVData.SCALP_INTERVALS:
            rec = self.__get_recommendation(symbol_pair, interval)
            if rec != TVData.BUY and rec != TVData.STRONG_BUY:
                return False
        return True

    def is_buy_long(self, symbol_pair: list) -> bool:
        """Get recommendations for all intervals in TVData. 
        Buy the coin if all intervals indicate a BUY or STRONG_BUY."""
        
        for interval in TVData.ALL_INTERVALS:
            rec = self.__get_recommendation(symbol_pair, interval)
            if rec != TVData.BUY and rec != TVData.STRONG_BUY:
                return False
        return True

    def is_strong_buy(self, symbol_pair: list) -> bool:
        for interval in TVData.SCALP_INTERVALS:
            recomendation = self.__get_recommendation(symbol_pair, interval)
            if recomendation != TVData.STRONG_BUY:
                return False
        return True

    def get_buy(self) -> set:
        """
        For every coin on the kraken exchange, 
        get the analysis to see which one is a buy according to the time intervals.
        
        """
        if not os.path.exists(KRAKEN_COINS):
            return []

        buy_set = set()

        with open(KRAKEN_COINS) as file:
            lines     = file.readlines()
            iteration = 1
            total     = len(lines)

            for symbol in sorted(lines):
                symbol = symbol.replace("\n", "")

                G.log_file.print_and_log(f"{iteration} of {total}: {symbol}")

                if symbol not in StableCoins.STABLE_COINS_LIST:
                    if self.is_buy(symbol+StableCoins.USD):
                        buy_set.add(symbol)
                iteration += 1
        return buy_set

    def get_buy_long(self) -> set:
        """
        For every coin on the kraken exchange, 
        get the analysis to see which one is a buy according to the time intervals.
        
        """
        if not os.path.exists(KRAKEN_COINS):
            return []

        buy_set = set()

        with open(KRAKEN_COINS) as file:
            lines     = file.readlines()
            iteration = 1
            total     = len(lines)

            for symbol in sorted(lines):
                symbol = symbol.replace("\n", "")

                G.log_file.print_and_log(f"{iteration} of {total}: {symbol}")

                if symbol not in StableCoins.STABLE_COINS_LIST:
                    if self.is_buy_long(symbol+StableCoins.USD):
                        buy_set.add(symbol)
                iteration += 1
        return buy_set



    def get_strong_buy(self) -> set:
        """
        For every coin on the kraken exchange, 
        get the analysis to see which one is a buy according to the time intervals.
        
        """
        if not os.path.exists(KRAKEN_COINS):
            return []

        buy_set = set()

        with open(KRAKEN_COINS) as file:
            lines     = file.readlines()
            iteration = 1
            total     = len(lines)

            for symbol in sorted(lines):
                symbol = symbol.replace("\n", "")

                G.log_file.print_and_log(f"{iteration} of {total}: {symbol}")

                if symbol not in StableCoins.STABLE_COINS_LIST:
                    if self.is_strong_buy(symbol+StableCoins.USD):
                        buy_set.add(symbol)
                iteration += 1
        return buy_set
