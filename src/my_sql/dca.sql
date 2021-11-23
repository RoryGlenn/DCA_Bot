CREATE TABLE safety_orders (
    symbol_pair         VARCHAR(20) NOT NULL,
    symbol              VARCHAR(10) NOT NULL,
    safety_order_no     INT         NOT NULL,
    deviation           FLOAT       NOT NULL,
    quantity            FLOAT       NOT NULL,
    total_quantity      FLOAT       NOT NULL,
    price               FLOAT       NOT NULL,
    average_price       FLOAT       NOT NULL, 
    required_price      FLOAT       NOT NULL,
    required_change     FLOAT       NOT NULL,
    profit              FLOAT       NOT NULL,
    cost                FLOAT       NOT NULL,
    total_cost          FLOAT       NOT NULL,
    order_placed        BOOLEAN     NOT NULL,
    so_key              INT         NOT NULL AUTO_INCREMENT,
    PRIMARY KEY (so_key)
);

CREATE TABLE open_buy_orders (
    symbol_pair    VARCHAR(20) NOT NULL,
    symbol         VARCHAR(10) NOT NULL,
    required_price FLOAT       NOT NULL,
    profit         FLOAT       NOT NULL,
    filled         BOOLEAN     NOT NULL,
    obo_txid       VARCHAR(30) PRIMARY KEY
);

CREATE TABLE open_sell_orders (
    symbol_pair VARCHAR(20) NOT NULL,
    symbol      VARCHAR(10) NOT NULL,
    profit      FLOAT       NOT NULL,
    cancelled   BOOLEAN     NOT NULL,
    filled      BOOLEAN     NOT NULL,
    oso_txid    VARCHAR(30) PRIMARY KEY
);

CREATE TABLE kraken_coins (
    symbol VARCHAR(10) NOT NULL
);
