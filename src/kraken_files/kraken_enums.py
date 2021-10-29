from enum import auto

EXCEL_FILES_DIRECTORY  = "src/kraken_files/excel_files"

KRAKEN_COINS = "src/kraken_files/txt_files/kraken_coins.txt"

TXIDS      = "txids"
QUANTITY   = 2
TXID_SHEET = "txids"

# DCA
BASE_ORDER  = 1
DECIMAL_MAX = 8
OPENPYXL    = "openpyxl"

class Buy_:
    BUY = auto()
    PRICES = auto()
    TIME_MINUTES = 1
    USD_TO_SPEND = auto()
    SET = set()

class DCA_:
    TARGET_PROFIT_PERCENT = auto()
    TRAILING_DEVIATION = auto()
    SAFETY_ORDERS_MAX = auto()
    SAFETY_ORDERS_ACTIVE_MAX = auto()
    SAFETY_ORDER_VOLUME_SCALE = auto()
    SAFETY_ORDER_STEP_SCALE = auto()
    SAFETY_ORDER_PRICE_DEVIATION = auto()

class ExportReport:
    DEFAULT_NAME = "my_trades"
    DEFAULT_FORMAT = "CSV"
    REPORT = "trades"
    DELETE = "delete"
    CANCEL = "cancel"


class Dicts:
    ORDER_MIN = "ordermin"
    PAIR_DECIMALS = "pair_decimals"
    LOT_DECIMALS = "lot_decimals"
    ALT_NAME = "altname"
    RESULT = "result"
    DECIMALS = "decimals"
    MINIMUM = "Minimum"
    ASSET = "Asset"
    DESCR = "descr"
    OPEN = "open"
    # For ticker information
    ASK_PRICE = "a"
    BID_PRICE = "b"
    LAST_TRADE_CLOSE = "c"
    VOLUME = "v"
    VOLUME_WEIGHTED_PRICE_AVG = "p"
    NUM_TRADES = "t"
    LOW = "l"
    HIGH = "h"
    # OPEN = "o"


class StableCoins:
    STABLE_COINS_LIST = ['ZUSD', 'USDT', 'BUSD', 'PAX', 'USDC', 'USD', 'TUSD', 'DAI', 'UST', 'HUSD', 'USDN',
                         'GUSD', 'FEI',  'LUSD', 'FRAX', 'SUSD', 'USDX', 'MUSD', 'USDK', 'USDS', 'USDP', 'RSV', 'USDQ', 'USDEX']
    ZUSD = "ZUSD"
    USD = "USD"
    USDT = "USDT"
    TRADE_FEE = 0.002


class Coins:
    BTC = "XXBT"
    ETH = "XETH"
    LTC = "XLTC"
    XLM = "XLM"
    DOGE = "XXDG"


class Trade:
    ZUSD = "ZUSD"
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop-loss"
    TAKE_PROFIT = "take-profit"
    STOP_LOSS_LIMIT = "stop-loss-limit"
    TAKE_PROFIT_LIMIT = "take-profit-limit"
    SETTLE_POSITION = "settle-position"
    BUY = "buy"
    SELL = "sell"
    RESULT = "result"
    MARKET_PRICE = "0"


class Method:
    # Market Data
    MARKET_DATA = "Ticker?pair="
    SERVER_TIME = "Time"
    SYSTEM_STATUS = "SystemStatus"
    ASSETS = "Assets"
    ASSET_PAIRS = "AssetPairs?pair="
    OHLC = "OHLC?pair="
    ORDER_BOOK = "Depth?pair="
    RECENT_TRADES = "Trades?pair="

    # User Data
    BALANCE = "Balance"
    TRADE_BALANCE = "TradeBalance"
    OPEN_ORDERS = "OpenOrders"
    CLOSED_ORDERS = "ClosedOrders"
    QUERY_ORDERS = "QueryOrders"
    TRADE_HISTORY = "TradesHistory"
    QUERY_TRADES = "QueryTrades"
    OPEN_POSITIONS = "OpenPositions"
    LEDGERS = "Ledgers"
    TRADE_VOLUME = "TradeVolume"
    ADD_EXPORT = "AddExport"
    EXPORT_STATUS = "ExportStatus"
    RETRIEVE_EXPORT = "RetrieveExport"
    REMOVE_EXPORT = "RemoveExport"

    # User Trading
    ADD_ORDER = "AddOrder"
    CANCEL_ORDER = "CancelOrder"
    CANCEL_ALL = "CancelAll"
    CANCEL_ALL_ORDERS_AFTER = "CancelAllOrdersAfter"

    # User Funding
    DEPOSIT_METHODS = "DepositMethods"
    DEPOSIT_ADDRESS = "DepositAddresses"
    DEPOSIT_STATUS = "DepositStatus"
    WITHDRAWL_INFO = "WithdrawInfo"
    WITHDRAWL = "Withdraw"
    WITHDRAWL_STATUS = "WithdrawStatus"
    WITHDRAWL_CANCEL = "WithdrawCancel"
    WALLET_TRANSFER = "WalletTransfer"

    # User Staking
    STAKE = "Stake"
    UNSTAKE = "Unstake"
    STAKEABLE_ASSETS = "Staking/Assets"
    PENDING = "Staking/Pending"
    TRANSACTIONS = "Staking/Transactions"

    # Websockets Authentication
    GET_WEBSOCKETS_TOKEN = "GetWebSocketsToken"


class Data:
    TXID = "txid"
    TRADES = "trades"
    USER_REF = "userref"
    DOCALCS = "docalcs"
    FEE_INFO = "fee-info"
    DESCRIPTION = "description"
    FORMAT = "format"
    REPORT = "report"
    ID = "id"
    TYPE = "type"
    ASSET = "asset"
    START = "start"
    PAIR = "pair"
    TIMEOUT = "timeout"
    ORDER_TYPE = "ordertype"
    TYPE = "type"
    VOLUME = "volume"
    VOL = "vol"
    PRICE = "price"
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop-loss"
    TAKE_PROFIT = "take-profit"
    STOP_LOSS_LIMIT = "stop-loss-limit"
    TAKE_PROFIT_LIMIT = "take-profit-limit"
    SETTLE_POSITION = "settle-position"
    BUY = "buy"
    SELL = "sell"
    METHOD = "method"
    NEW = "new"
    KEY = "key"
    AMOUNT = "amount"
    REFID = "refid"
    FROM = "from"
    TO = "to"
    MARKET_PRICE = "0"
    ORDER_TXID = "ordertxid"
    CC_PAIR = 'close[pair]'
    CC_TYPE = 'close[type]'
    CC_ORDER_TYPE = 'close[ordertype]'
    CC_PRICE = 'close[price]'
    CC_VOLUME = 'close[volume]'


class Nap:
    NORMAL = 1
    LONG = 2


class FileMode:

    """
    Open text file for reading.  The stream is positioned at the
        beginning of the file.    
    """
    READ_ONLY = "r"

    """
    Open for reading and writing.  The stream is positioned at the
        beginning of the file.
    """
    READ_WRITE = "r+"

    """
    Truncate file to zero length or create text file for writing.
         The stream is positioned at the beginning of the file.    
    """
    WRITE_TRUNCATE = "w"

    """
    Open for reading and writing.  The file is created if it does not
         exist, otherwise it is truncated.  The stream is positioned at
         the beginning of the file.
         """
    READ_WRITE_CREATE = "w+"

    """
    Open for writing.  The file is created if it does not exist.  The
        stream is positioned at the end of the file.  Subsequent writes
        to the file will always end up at the then current end of file,
        irrespective of any intervening fseek(3) or similar.
    """

    WRITE_APPEND = "a"

    """
   Open for reading and writing.  The file is created if it does not
        exist.  The stream is positioned at the end of the file.  Subse-
        quent writes to the file will always end up at the then current
        end of file, irrespective of any intervening fseek(3) or similar.
    
    """
    READ_WRITE_APPEND = "a+"

    """
    Configuration file for the rake bot to use on users account and wallets
    """
    CONFIG_FILE = 'src/kraken_files/txt_files/config.txt'


class Misc:
    CLS = "cls"
    CLEAR = "clear"

class KrakenFiles:
    WITHDRAWAL_MINIMUMS = "src/kraken_files/csv_files/Withdrawal_Minimums_and_Fees.csv"
    ORDER_SIZE_MINIMUMS = "src/kraken_files/csv_files/Minimum_Order_Sizes.csv"
    DEPOSIT_MINIMUMS = "src/kraken_files/csv_files/Deposit_Minimums_and_Fees.csv"
    DEPOSIT_CONFIRMATIONS = "src/kraken_files/csv_files/Deposit_Confirmation.csv"

class ConfigKeys:
    # kraken
    KRAKEN_API_KEY = "kraken_api_key"
    KRAKEN_SECRET_KEY = "kraken_secret_key"

    # buy
    BUY_SET = "buy_list"

    # dca
    DCA_TARGET_PROFIT_PERCENT = "dca_target_profit_percent"
    # DCA_TRAILING_DEVIATION = "dca_trailing_deviation"
    DCA_BASE_ORDER_SIZE = "dca_base_order_size"
    DCA_SAFETY_ORDERS_MAX = "dca_safety_orders_max"
    DCA_SAFETY_ORDERS_ACTIVE_MAX = "dca_safety_orders_active_max"
    DCA_SAFETY_ORDER_SIZE = "dca_safety_order_size"
    DCA_SAFETY_ORDER_VOLUME_SCALE = "dca_safety_order_volume_scale"
    DCA_SAFETY_ORDER_STEP_SCALE = "dca_safety_order_step_scale"
    DCA_SAFETY_ORDER_PRICE_DEVIATION = "dca_safety_order_price_deviation"

class Threads:
    BUY = "thread_buy"
    SELL = "thread_sell"
    DISTRIBUTION = "thread_distribution"

class DFColumns:
    SYMBOL = "Symbol"
    AVERAGE_PRICE = "Average Price"
    QUANTITY = "Quantity"

class SOColumns:
    SAFETY_ORDER_NO = "Safety Order No."
    DEVIATION = "Deviation, %"
    QUANTITY = "Quantity"
    PRICE = "Price $"
    AVG_PRICE = "Average Price $"
    REQ_PRICE = "Required price"
    REQ_CHANGE_PERC = "Required Change %"

class OBOColumns:
    TXIDS = "txids"
    REQ_PRICE = "required_price"

class OSOColumns:
    TXIDS = "txids"

class SheetNames:
    SAFETY_ORDERS = "safety_orders"
    OPEN_BUY_ORDERS = "open_buy_orders"
    OPEN_SELL_ORDERS = "open_sell_orders"
