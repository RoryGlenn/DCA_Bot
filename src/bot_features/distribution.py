#!/usr/bin/env python

"""distribution.py - 

Waits until Sunday at UTC midnight.
Distributes money to another kraken account to act as a warchest

What is the difference between __transfer_to_external_wallet and distribution loop?

"""

import datetime
import math
from pprint import pprint

import pandas as pd
import pause
from kraken_files.kraken_enums import Distribution_, StableCoins
from util.globals import G

from bot_features.base import Base

DAYS_IN_A_WEEK         = 7
WEEKS_IN_A_YEAR        = 52
ONE_WEEK               = 1
DISTRIBUTION_LIMIT_USD = 1500
UTC_MIDNIGHT_HOUR      = 18 # this is relative to denver, colorado

class Distribution(Base):
    def __init__(self, parameter_dict: dict) -> None:
        """
        Returns new  object with specified data

        """

        super().__init__(parameter_dict)
        
        self.withdrawal_mins                 = pd.DataFrame()
        self.withdrawal_minimum:       float = 0.0
        self.withdrawal_max_precision: float = 0.0
        
        self.distribute_quantity:      float = 0.0
        self.distribute_usd:           float = 0.0
        self.distribute_wait_time            = None
        self.distribute_start_day            = datetime.datetime
        self.distribute_days:          dict  = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}        

    def __get_quantity_to_distribute(self) -> None:
        """Converts USD to the TRANSFER_SYMBOL quantity"""
        distribute_quantity       = self.distribute_usd / self.ask_price
        transfer_symbol_qty_owned = self.account_balance[Distribution_.SYMBOL]
        
        if transfer_symbol_qty_owned < self.distribute_quantity:
            """if the qty_owned is less than the quantity to transfer,
            set quantity_to_transfer to qty_owned because thats all we have."""
            distribute_quantity = transfer_symbol_qty_owned
        return self.round_decimals_down(distribute_quantity, self.withdrawal_max_precision)

    def __set_wait_time(self) -> None:
        """Returns days, hours, minutes and seconds to wait until TRANSFER_DAY"""
        today             = datetime.date.today()
        time_now          = datetime.datetime.now()

        days_to_wait = (
            self.distribute_days[Distribution_.DISTRIBUTE_DAY] - today.weekday()) % DAYS_IN_A_WEEK

        if datetime.date.today().weekday() == self.distribute_days[Distribution_.DISTRIBUTE_DAY]:
            if time_now.hour >= UTC_MIDNIGHT_HOUR:
                days_to_wait = DAYS_IN_A_WEEK

        wake_up = datetime.datetime.now() + datetime.timedelta(days=days_to_wait)
        future = datetime.datetime(wake_up.year, wake_up.month, wake_up.day,
                                   UTC_MIDNIGHT_HOUR)
        self.distribute_wait_time = future
        return

    def __get_current_week(self) -> int:
        """Count how many weeks it has been since self.transfer_start_day
        Because we start counting the number of weeks from 1 instead of 0, the possible outcomes are 1 to 52
        
        """

        transfer_start_day = datetime.datetime(year=2021, month=9, day=12, hour=18)
        transfer_end_day   = datetime.datetime(year=2022, month=9, day=12, hour=18)
        today              = datetime.date.today()

        days_from_transfer_start_day = today - \
            datetime.date(year=transfer_start_day.year,
                          month=transfer_start_day.month, day=transfer_start_day.day)
        weeks_from_transfer_start_day = days_from_transfer_start_day.days // DAYS_IN_A_WEEK
        
        # If this program has been run for longer than 1 year (52 weeks), set a limit at 52 weeks from transfer_start_day 
        if weeks_from_transfer_start_day >= WEEKS_IN_A_YEAR:
            weeks_from_transfer_start_day = WEEKS_IN_A_YEAR - ONE_WEEK
        return weeks_from_transfer_start_day + ONE_WEEK

    def __get_weekly_usd_to_distribute(self) -> int:
        """
        Given that we want to transfer once a week, every week for a year, 
        Return the maximum amount of usd to transfer given the current week
        
        On a linear graph: if the transfer limit is set to 1500, the usd transfer amount will be: 1500 / 52 (weeks in a year)].
        This give us a rate of change (slope) of $28.84 each week

        To get the usd to transfer given any arbitrary week in range [1 - 52], multiply 28.84 with the number of weeks it has been since the transfer start date.
        This gives us a final result of $28.84x

        y    = a * log(x) + b
        1500 = a * log(52) + 28
        1472 = a * 1.716
        So this formula would get you there: f(x) = 858 * log(x) + 28

        """

        a   = 857.80
        b   = 28.84
        log = math.log10(self.__get_current_week())
        usd_to_transfer = (a*log) + b

        if usd_to_transfer > DISTRIBUTION_LIMIT_USD:
            usd_to_transfer = DISTRIBUTION_LIMIT_USD
        return usd_to_transfer
        
    def __set_distribute_variables(self) -> None:
        """Sets all variables needed to transfer"""
        self.account_balance          = self.get_parsed_account_balance()
        self.withdrawal_minimum       = self.get_withdrawal_minimum(Distribution_.SYMBOL)
        self.withdrawal_max_precision = self.get_withdrawal_precision_max(Distribution_.SYMBOL)
        self.ask_price                = self.get_ask_price(Distribution_.SYMBOL+StableCoins.ZUSD)
        self.distribute_usd           = self.__get_weekly_usd_to_distribute()
        self.distribute_quantity      = self.__get_quantity_to_distribute()
        return


##################################################################################################################################
# DISTRIBUTE_LOOP
##################################################################################################################################
    def distribute_loop(self) -> None:
        """
        Distribute loop

        """

        while True:
            try:
                self.__set_wait_time()
                G.log_file.print_and_log(f"distribute_loop: Waiting till {self.distribute_wait_time} to transfer")
                pause.until(self.distribute_wait_time)
                
                self.__set_distribute_variables(self)

                if self.distribute_quantity < self.withdrawal_minimum:
                    G.log_file.print_and_log(f"distribute_loop: {self.withdrawal_minimum} does not meet the {Distribution_.SYMBOL} withdrawal minimum")
                    continue

                self.withdraw_result = self.withdraw_funds(asset=Distribution_.SYMBOL, key=Distribution_.DISTRIBUTE, amount=self.distribute_quantity)
                pprint(self.withdraw_result)

            except Exception as e:
                G.log_file.print_and_log(message="distribute_loop:", e=e)
        return
