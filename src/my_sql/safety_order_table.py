import pandas as pd

class SOT():
    def __init__(self) -> None:
        self.table = pd.DataFrame()
        self.column_names = [
            "symbol_pair",
            "symbol",
            "safety_order_no",
            "deviation",
            "quantity",
            "total_quantity",
            "price",
            "average_price",
            "required_price",
            "required_change",
            "profit",
            "order_placed",
            "so_key"]
        return

    def init_table(self) -> None:
        self.table = pd.DataFrame(columns=self.column_names)
        return