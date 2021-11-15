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
);

CREATE TABLE open_buy_orders (
    symbol_pair    VARCHAR(20) NOT NULL,
    required_price FLOAT       NOT NULL,
    profit         FLOAT       NOT NULL,
    filled         BOOLEAN     NOT NULL,

    obo_txid           VARCHAR(30) PRIMARY KEY -- new

    -- bo_key         INT         NOT NULL,
    -- PRIMARY KEY (bo_key),
    -- FOREIGN KEY (bo_key) REFERENCES safety_orders(so_key)
);

CREATE TABLE open_sell_orders (
    symbol_pair VARCHAR(20) NOT NULL,
    profit      FLOAT       NOT NULL,
    filled      BOOLEAN     NOT NULL,

    oso_txid        VARCHAR(30) PRIMARY KEY -- new

    -- oso_key     INT         NOT NULL,
    -- FOREIGN KEY (oso_key) REFERENCES open_buy_orders(bo_key)
);
