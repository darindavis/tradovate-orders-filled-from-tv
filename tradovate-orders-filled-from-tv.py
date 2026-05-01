r"""
File: tradovate-orders-filled-from-tv.py
Desc: Summarize one day's Tradovate trade history (orders filled) exported from TradingView. Futures day trades only (all positions open and close same day).
Input: CSV export from TradingView (Downloads\tradovate-orders-filled.csv)
Output: Shell.
Usage: See usage()
Author: Darin Davis, Copyright 2026
History:
    4/30/26: Initial version
    5/1/26: Fix pandas text wrapping.
"""

"""
                    IMPORTS
"""
import pandas as pd
import sys
from pathlib import Path
from datetime import date, datetime
import re

"""
                    GLOBAL VARIABLES
"""

downloads_folder = Path.home() / "Downloads" # full path to current user's Downloads folder


"""
                    FUNCTIONS
"""

def usage():
    print("\nUsage:", sys.argv[0], "[YYYY-MM-DD] (default = today)")
    print("\nExport steps: In TradingView > Trade > Tradovate")
    print("\tOrders > Filled")
    print("\tExport data > Orders > Export\n")


def debug(msg=""):
    debug_flag = False

    if debug_flag:
        line = sys._getframe(1).f_lineno # 1 = caller's line number
        # print(f"DEBUG [{__file__}:{line}] {msg}")
        print(f"DEBUG [{line}] {msg}")


"""
                    Convert futures points to dollar equivalent
"""
def price_chg_to_dollars(symbol, price_chg):

    # Define regex pattern for a futures contract symbol (mini or micro)
    pattern = re.compile(r"^(.?)(..)[A-Z][0-9]$")

    match = pattern.match(symbol) # eval ticker
    if match: # extract the contract abbreviation from the symbol
        type = match.group(1) # micro or mini; or 'R' in 'RTY'?
        abbrev = match.group(2) # isolate the two-letter abbreviation or 'TY' in 'RTY'
        debug(f"Processing {type}.{abbrev}, {price_chg:.2f}")

    # compute dollar value for a mini (price change / tick size * tick value)
    match abbrev:
        case "CL":
            dollar = price_chg / 0.01 * 10
        case "GC":
            dollar = price_chg / 0.1 * 10
        case "ES":
            dollar = price_chg / 0.25 * 12.5
        case "NQ":
            dollar = price_chg / 0.25 * 5
        case "TY" | "2K":
            dollar = price_chg / 0.1 * 5
        case "YM":
            dollar = price_chg / 1.0 * 5
        case _: # unrecognized symbol
            dollar = 0
            print(f"unrecognized abbreviation {abbrev}")

    debug(f"dollar value for a mini = {dollar:.2f}")
    # compute dollar value for a micro
    if type == 'M':
        dollar = dollar / 10
        debug(f"dollar value for a micro = {dollar:.2f}")

    return dollar


"""
                    MAIN CODE
"""
def main():

    this_date = date.today().strftime('%Y-%m-%d') # default date of trades to analyze

    if len(sys.argv) > 1: # check if user provided date
        this_date = sys.argv[1] # first argument after script name
        try:
            test_date = datetime.strptime(this_date, '%Y-%m-%d')
        except:
            print(f"Date must be in format YYYY-MM-DD not {this_date}")
            usage()
            sys.exit(1)


    # define the filename of the trade history file
    in_file = downloads_folder / "tradovate-orders-filled.csv"

    # load the history file into a dataframe
    try:
        if in_file.exists():
            # print(f"File '{in_file}' exists!")
            if in_file.is_file():
                # print("It's a regular file.")
                history = pd.read_csv(in_file)
        else:
            print(f"File '{in_file}' does not exist.")
    except Exception as e:
        print(f"Error: {e}")


    print(f"\nTrade history for {this_date}")

    # Convert Time column to datetime
    history['Update Time'] = pd.to_datetime(history['Update Time'])

    # filter out all dates except for this_date
    daily_history = history[history['Update Time'].dt.date == pd.to_datetime(this_date).date()].copy()

    if daily_history.empty:
        print("No trades on this date")
        usage()
        exit(1)

    # remove unneded columns
    daily_history.drop(['Qty', 'Remaining Qty', 'Limit Price', 'Stop Loss', 'Stop Price', 'Take Profit', 'Expiry', 'Expiry Time', 'Order ID'], axis=1, inplace=True)

    ### create columns for aggregation ###

    # create column reflecting negative quantity for sells
    daily_history['net_qty'] = daily_history['Filled Qty'].where(daily_history['Side'] == 'Buy', -daily_history['Filled Qty'])

    # Syntax: keep original value if condition is True; replace it with other value if condition is False
    daily_history['buy_qty'] = daily_history['Filled Qty'].where(daily_history['Side'] == 'Buy', 0)
    daily_history['sell_qty'] = daily_history['Filled Qty'].where(daily_history['Side'] == 'Sell', 0)
    daily_history['buy_price'] = daily_history['Avg Fill Price'].where(daily_history['Side'] == 'Buy', 0)
    daily_history['sell_price'] = daily_history['Avg Fill Price'].where(daily_history['Side'] == 'Sell', 0)
    daily_history['ext_buy_price'] = daily_history['buy_price'] * daily_history['buy_qty']
    daily_history['ext_sell_price'] = daily_history['sell_price'] * daily_history['sell_qty']
    # print(daily_history.info())
    print("\nDaily history with extended prices for aggregation:")
    print(daily_history)

    # for each unique symbol, sum the number and price value of contracts bought and sold
    net_positions = (daily_history
                    .groupby('Symbol')
                    .agg(
                        net_qty=('net_qty', 'sum'),
                        total_buy_qty=('buy_qty', 'sum'),
                        total_sell_qty=('sell_qty', 'sum'),
                        total_buy_price=('ext_buy_price', 'sum'),
                        total_sell_price=('ext_sell_price', 'sum'),
                    )
                    .reset_index())

    net_positions['net_price_chg'] = net_positions['total_sell_price'] - net_positions['total_buy_price']
    # print("\nAggregate columns:")
    # print(net_positions)

    # convert ticks to dollars
    net_positions['PnL'] = net_positions.apply(lambda row: price_chg_to_dollars(row['Symbol'], row['net_price_chg']), axis=1)
    # apply() is an iterator function of a dataframe; axis=1 means "iterate through all rows" i.e. apply the lambda function to each row
    # "row" is an arbitrary (but conventional) variable name (not a keyword) that identifes a single row passed as the argument to the lambda

    print("\nPnL per symbol:")
    print(net_positions)

    # compute total PnL for all symbols
    total_pnl = net_positions['PnL'].sum()
    print(f"\nTotal PnL: {total_pnl:.2f}\n")

    # check to ensure all contracts closed
    if (net_positions['net_qty'] != 0).any():
        print("The following symbols have non-zero net quantity:")
        print(net_positions[net_positions['net_qty'] != 0].to_string(index=False))
    else:
        print("All positions are flat (net_qty = 0 for all symbols).")


if __name__ == "__main__":
    main()