"""tip.py: Sends a tip to TIP_ADDRESS based on users config file"""

from pprint import pprint

from kraken_files.kraken_enums import (Coins, ExternalWallet, StableCoins,
                                       Tip_, Trade)
from util.globals import G

from bot_features.base import Base

KRAKEN_USD_LIMIT   = 1500
USD_DECIMAL_PLACES = 2


class Tip(Base):
    def __init__(self, parameter_dict: dict) -> None:
        """
        Returns new Spot object with specified data
        
        """
        super().__init__(parameter_dict)
        self.tradeable_pair:      str   = ""
        self.ask_price:           float = 0.0
        self.btc_ask_price:       float = 0.0
        self.order_min:           float = 0.0
        self.withdrawal_min:      float = 0.0
        self.usd_to_convert:      float = 0.0
        self.value:               float = 0.0
        self.quantity_to_buy:     float = 0.0 
        self.usd_balance:         float = 0.0
        self.withdrawal_prec_max: int   = 0

    def __set_tip_variables(self) -> None:
        """Set the variables for the Tip struct."""
        self.usd_to_convert      = self.usd_balance * ExternalWallet.PERCENT
        self.tradeable_pair      = self.get_tradable_asset_pair(Tip_.SYMBOL)
        self.ask_price           = self.get_ask_price(self.tradeable_pair)
        self.order_min           = self.get_order_min(Tip_.SYMBOL)
        self.withdrawal_min      = self.get_withdrawal_minimum(Tip_.SYMBOL)
        self.withdrawal_prec_max = self.get_withdrawal_precision_max(Tip_.SYMBOL)
        self.usd_to_convert      = self.round_decimals_down(self.usd_to_convert*Tip_.PERCENT)
        self.value               = self.order_min * self.ask_price
        self.quantity_to_buy     = self.usd_to_convert / self.ask_price
        return


    def __print_result(self, message: str, message_error: str, result: dict) -> None:
        if self.has_result(result):
            G.log_file.print_and_log(f"{message}: {result}")
        else:
            G.log_file.print_and_log(f"{message_error}: {result}")
        return

    def __tip(self) -> None:
        """
        Sends TIP_PERCENT of raked money to TIP_ADDRESS every time try_transfer() is called
        
        """
        try:
            self.__set_tip_variables()

            # 1. Check order min
            if self.usd_to_convert < self.value:
                G.log_file.print_and_log(f"tip_and_transfer_loop: TIP: {Tip_.SYMBOL} order minimum is {self.order_min}")
                return

            tip_result = self.market_order(Trade.BUY, self.quantity_to_buy, self.tradeable_pair)

            if not self.has_result(tip_result):
                G.log_file.print_and_log(f"tip_and_transfer_loop: TIP: could not tip {tip_result}")
                return

            G.log_file.print_and_log(f"tip_and_transfer_loop: Successful buy of {self.tradeable_pair}: {tip_result}")
            
            # send the tip to Tip_.TIP_ADDRESS
            withdrawal_amount = self.round_decimals_down(self.quantity_to_buy, self.withdrawal_prec_max)
            withdraw_result = self.withdraw_funds(asset=Tip_.SYMBOL, key=Tip_.ADDRESS, amount=withdrawal_amount)
            self.__print_result(f"TIP: Successful transfer to {Tip_.ADDRESS}", f"TIP: could not withdraw {Tip_.SYMBOL} to {Tip_.ADDRESS}", withdraw_result)
        except Exception as e:
            G.log_file.print_and_log("tip_and_transfer_loop: could not make tip", e=e)
            return

    def __get_external_wallet_variables(self) -> None:
        """Get the variables needed to make a transfer to the external wallet."""
        usd_to_convert     = self.get_coin_balance(StableCoins.ZUSD) * ExternalWallet.PERCENT
        usd_to_convert     = self.round_decimals_down(usd_to_convert, USD_DECIMAL_PLACES)
        self.btc_ask_price = self.get_ask_price(Coins.BTC+StableCoins.ZUSD)
        btc_max_precision  = self.get_max_volume_precision(Coins.BTC)
        
        # convert usd qty into btc qty
        btc_qty = self.round_decimals_down(
            self.convert_quantities(self.get_coin_balance(StableCoins.ZUSD), self.btc_ask_price), btc_max_precision)
        return usd_to_convert, btc_qty 

    def __transfer_to_external_wallet(self) -> None:
        """Transfer funds to external wallet (ExternalWallet.ADDRESS)."""
        usd_to_convert, btc_qty = self.__get_external_wallet_variables()
        btc_quantity_to_buy     = btc_qty * 0.24 # Ben wants 24% of BTC to be left in account ### BTC_RAKE_PERCENT

        # substract the amount of btc from usd_to_convert
        btc_value_in_usd = self.btc_ask_price * btc_quantity_to_buy
        usd_to_convert  -= btc_value_in_usd

        # from usd_to_convert, convert 24% into bitcoin and leave it in kraken account
        usd_to_btc_result = self.market_order(Trade.BUY, btc_quantity_to_buy, Coins.BTC+StableCoins.ZUSD)
        self.__print_result("Bought BTCUSD: ", "could not buy BTCUSD: ", usd_to_btc_result)

        # convert USD into USDT
        usd_to_usdt_result = self.market_order(Trade.BUY, usd_to_convert, StableCoins.USDT+StableCoins.ZUSD)
        self.__print_result("Bought USDTUSD:", "could not buy USDTUSD", usd_to_usdt_result)

        usdt             = self.get_coin_balance(StableCoins.USDT)
        usdt_to_transfer = usdt - (usdt * Tip_.PERCENT)

        # usdt_to_transfer won't work unless we reduce it by some percentage, 0.95 currently works.
        usdt_to_transfer = self.round_decimals_down(usdt_to_transfer*0.97, 2)
        withdraw_result  = self.withdraw_funds(asset=StableCoins.USDT, key=ExternalWallet.ADDRESS, amount=usdt_to_transfer)
        self.__print_result("Transferred USDT to wallet:", "Failed to transfer USDT to wallet", withdraw_result)
        return

    def tip_and_transfer_to_external_wallet(self) -> None:
        """
        If kraken account has more than Spot_.USD_WALLET_LIMIT,
        convert half of the USD into USDT and transfer it to another wallet for safe keeping.
        
        """
        try:
            self.usd_balance = self.get_coin_balance(StableCoins.ZUSD)
            if self.usd_balance <= ExternalWallet.USD_LIMIT:
                return

            self.__tip()
            self.__transfer_to_external_wallet()

        except Exception as e:
            G.log_file.print_and_log(message=f"tip_and_transfer_to_external_wallet: tip or transfer to external wallet failed", e=e)
        return
        