r"""
File: t2t.py (tradovate-to-tradingview)
Desc: Sometimes the trade history (orders filled) exported from TradingView is missing some rows that are present in the Tradovate export.
      This script reads the Tradovate export and generates a CSV file that matches the column structure exported from TradingView.
Input: CSV export from Tradovate (Downloads/fills.csv)
Output: CSV file with the same column structure as the TradingView export (Downloads/tradovate-orders-filled.csv)
Usage: See usage()
Author: Darin Davis, Copyright 2026
History:
    8/13/26: Initial version
    8/21/26: Sort tradovate by increasing 'Update Time'.
"""

"""
                    IMPORTS
"""
import pandas as pd
import sys
from pathlib import Path

"""
                    GLOBAL VARIABLES
"""

tradovate_folder = Path.home() / "Downloads" # full path to current user's Downloads folder


"""
                    FUNCTIONS
"""

def usage():
    script_name = Path(sys.argv[0]).name
    print("\nUsage:", script_name)
    tips = r"""
Export steps: In Tradovate > "DAY MARGIN / INITIAL MARGIN" box > Fills > Download CSV
"""
    print(tips)


def debug(msg=""):
    debug_flag = False

    if debug_flag:
        frame = sys._getframe(1) # 1 = caller's frame
        line = frame.f_lineno # 1 = caller's line number
        func_name = frame.f_code.co_name # function name of caller
        # print(f"DEBUG [{__file__}:{line}] {msg}")
        print(f"DEBUG [{func_name}:{line}] {msg}")


def main():
    """
                        MAIN CODE
    """

    # define the filename of the trade history file
    in_file = tradovate_folder / "fills.csv"

    # load the fills file into a dataframe
    try:
        if in_file.exists():
            debug(f"File '{in_file}' exists!")
            if in_file.is_file():
                debug("It's a regular file.")
                tradovate = pd.read_csv(in_file)
        else:
            print(f"File '{in_file}' does not exist.")
    except Exception as e:
        print(f"Error: {e}")

    # tradovate.drop(['_priceFormat', '_priceFormatType', '_tickSize', '_action'], axis=1, inplace=True)

    tradovate = tradovate.rename(columns={
        'Contract': 'Symbol',
        'B/S': 'Side',
        '_qty': 'Qty',
        'Quantity': 'Filled Qty',
        'Price': 'Avg Fill Price',
        'Timestamp': 'Update Time',
        # placeholders below for columns that are present in the TradingView export but not in the Tradovate export
        '_action': 'Type',
        '_id': 'Remaining Qty',
        'Product': 'Limit Price',
        '_contractId': 'Stop Price',
        '_tickSize': 'Take Profit',
        '_priceFormat': 'Stop Loss',
        '_active': 'Expiry',
        '_timestamp': 'Expiry Time'
    })

    tradovate = tradovate[['Symbol', 'Side', 'Type', 'Qty', 'Remaining Qty', 'Filled Qty', 'Limit Price', 'Stop Price', 'Take Profit',
                           'Stop Loss', 'Avg Fill Price', 'Update Time', 'Order ID', 'Expiry', 'Expiry Time']]
    tradovate.sort_values(['Update Time'], inplace=True) # sort trades by increasing time (oldest first)

   # save results to CSV
    out_file = tradovate_folder / "tradovate-orders-filled.csv"
 
    with open(out_file, "w", encoding='utf-8') as f:
        tradovate.to_csv(f, index=False, sep=',', lineterminator='\n')

if __name__ == "__main__":
    main()