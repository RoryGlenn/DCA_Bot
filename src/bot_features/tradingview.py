from tradingview_ta import TA_Handler, Interval
from pprint import pprint


class TVData:
    SCREENER       = "crypto"
    EXCHANGE       = "kraken"
    RECOMMENDATION = "RECOMMENDATION"
    BUY            = "BUY"
    STRONG_BUY     = "STRONG_BUY"
    INTERVALS = [
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
            pprint(e)
        return []

    def is_buy(self, symbol_pair: list):
        """Get recommendations for all intervals in TVData. 
        Buy the coin if all intervals indicate a BUY or STRONG_BUY."""
        
        for interval in TVData.INTERVALS:
            rec = self.__get_recommendation(symbol_pair, interval)
            if rec != TVData.BUY and rec != TVData.STRONG_BUY:
                return False
        return True
