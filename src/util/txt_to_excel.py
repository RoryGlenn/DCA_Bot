import pandas as pd

TXT_PATH   = "src/entry_prices/entry_prices.txt"
EXCEL_PATH = "src/entry_prices/entry_prices.xlsx"
ENGINE     = "openpyxl"


def create_entry_price_dict() -> None:
    """
    Creates a dictionary (symbol, price) based on the user specified
    buy_list in the config file.

    """

    entry_price_dict = dict()
    
    with open(TXT_PATH, 'r') as file:
        for line in sorted(file.readlines()):
            line = line.split()
            entry_price_dict[str(line[0]).upper()] = float(line[1])
    return entry_price_dict


def write_to_excel(entry_prices: pd.DataFrame) -> None:
    """Writes to excel file"""
    with pd.ExcelWriter(EXCEL_PATH, engine=ENGINE, mode="w") as writer:
        entry_prices.to_excel(writer, sheet_name="Entry Prices", index=False)
    return


if __name__ == "__main__":
    entry_prices = pd.DataFrame.from_dict(create_entry_price_dict(), orient='index')
    write_to_excel(entry_prices)


    