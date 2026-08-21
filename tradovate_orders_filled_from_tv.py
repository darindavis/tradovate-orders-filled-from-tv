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
    5/12/26: Add report file. Sort history by increasing 'Update Time'.
    5/27/26: Add calc for total PnL less fees.
    5/28/26: Improve calculation of fees on per ticker basis.
    6/3/26: Created pytest tests. Add calc_percent_return(). Add name of calling function to debug output.
    6/4/26: Fix bug in calc_percent_return() and test_calc_percent_return().
    7/7/26: Add ES and YM to get_fee().
    7/14/26: Add rounding to 2 decimal places for PnL% column.
    7/15/26: Add tip to usage() for editing symbols in the exported CSV when there are multiple trades for the same symbol.
    7/23/26: Add rounding to 2 decimal places for net_price_chg column.
    7/24/26: Add strip() to remove leading/trailing whitespace from 'Side' column in daily_history.
             In rare cases, TradingView doesn't export all the rows that are in the Tradovate export. The Tradovate export has a leading
             space in the 'Side' column. When those rows are copied into the TradingView export, the leading space must be removed.
    7/24/26: Add fee to each trade line item.
    8/13/26: Add debug statements when loading history file.
    8/21/26: Sort daily_history by increasing 'Update Time'.
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
    script_name = Path(sys.argv[0]).name
    print("\nUsage:", script_name, "[YYYY-MM-DD] (default = today)")
    tips = r"""
Export steps: In TradingView > Trade > Tradovate
    Orders > Filled
    Export data > Orders > Export

Tip: If there are multiple trades for the same symbol, edit the exported CSV and replace the trailing
integer in the symbol with a unique integer for each trade. For example, if there are two trades
for MESM6, change the symbol for the first trade to MESM1 and the second trade to MESM2.
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


def get_fee(symbol):
    """
    Returns the fee for the symbol supplied as an argument. The fees are as follows:
        Apex fees (https://apextraderfunding.com/help-center/tradovate/tradovate-commission-instruments/):
            MES: $0.52
            MNQ: $0.52
            M2K: $0.52
            MYM: $0.52
            MCL: $0.67
            MGC: $0.67
    """
    pattern = re.compile(r"^(.?)(..)[A-Z][0-9]$")

    match = pattern.match(symbol) # eval ticker
    if match: # extract the contract abbreviation from the symbol
        type = match.group(1) # micro or mini; or 'R' in 'RTY'?
        abbrev = match.group(2) # isolate the two-letter abbreviation or 'TY' in 'RTY'
        debug(f"Processing {type}.{abbrev}")
    else:
        print(f"unrecognized symbol {symbol}")
        return 0

    match abbrev:
        case "ES":
            fee = 0.52
        case "NQ":
            fee = 0.52
        case "2K":
            fee = 0.52
        case "YM":
            fee = 0.52
        case "CL":
            fee = 0.67
        case "GC":
            fee = 0.67
        case _: # unrecognized symbol
            fee = 0
            print(f"unrecognized abbreviation {abbrev}")

    # debug(f"fee for a mini = {fee:.2f}")
    # if type == 'M':
    #     fee = fee / 10
    #     debug(f"fee for a micro = {fee:.2f}")

    return fee


def price_chg_to_dollars(symbol, price_chg):
    """
                        Convert futures points to dollar equivalent
    """

    # Define regex pattern for a futures contract symbol (mini or micro)
    pattern = re.compile(r"^(.?)(..)[A-Z][0-9]$")

    match = pattern.match(symbol) # eval ticker
    if match: # extract the contract abbreviation from the symbol
        type = match.group(1) # micro or mini; or 'R' in 'RTY'?
        abbrev = match.group(2) # isolate the two-letter abbreviation or 'TY' in 'RTY'
        debug(f"Processing {type}.{abbrev}, {price_chg:.2f}")
    else:
        print(f"unrecognized symbol {symbol}")
        return 0

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


def calc_percent_return(symbol, num_contracts, PnL):
    """
        Calculates the percentage return on margin for the trade.
        Return value is a decimal (e.g. 0.02 = 2% return).
        The margin rate varies by symbol and market conditions, so this calculation is just an estimate.
        Tradovate distinguishes between "day margin" (much lower) and "initial (overnight) margin" (much higher).
        The day margin is used for day trades only. Day margin rates:
        https://www.tradovate.com/resources/markets/margin/?term=mnq
    """

    # protect against divide by zero
    if num_contracts < 1:
        print(f"Need at least 1 contract for {symbol}")
        return 0

    # Define regex pattern for a futures contract symbol (mini or micro)
    pattern = re.compile(r"^(.?)(..)[A-Z][0-9]$")

    match = pattern.match(symbol) # eval ticker
    if match: # extract the contract abbreviation from the symbol
        type = match.group(1) # micro or mini; or 'R' in 'RTY'?
        abbrev = match.group(2) # isolate the two-letter abbreviation or 'TY' in 'RTY'
        debug(f"Processing {type}.{abbrev}, {num_contracts} contracts, PnL ${PnL:.2f}")
    else:
        print(f"unrecognized symbol {symbol}")
        return 0

    # compute percent return for a mini (PnL / (num_contracts * margin))
    match abbrev:
        case "ES":
            pcnt_return = PnL / ( num_contracts * 500 )
        case "NQ":
            pcnt_return = PnL / ( num_contracts * 1000 )
        case "TY" | "2K":
            pcnt_return = PnL / ( num_contracts * 500 )
        case "YM":
            pcnt_return = PnL / ( num_contracts * 500 )
        case "CL":
            pcnt_return = PnL / ( num_contracts * 1000 )
        case "GC":
            pcnt_return = PnL / ( num_contracts * 2000 )
        case _: # unrecognized symbol
            pcnt_return = 0
            print(f"unrecognized abbreviation {abbrev}")

    debug(f"percent return for a mini = {pcnt_return:.4f}")

    # compute percent return for a micro
    if type == 'M':
        pcnt_return = pcnt_return * 10
        debug(f"percent return for a micro = {pcnt_return:.4f}")

    return pcnt_return


def main():
    """
                        MAIN CODE
    """

    # Force pandas to show all columns and allow wrapping
    pd.set_option('display.max_columns', None)      # show every column
    pd.set_option('display.width', None)            # auto-detect terminal width (or set a large number like 2000)
    pd.set_option('display.max_colwidth', None)     # don't truncate individual cell content
    pd.set_option('display.expand_frame_repr', True)  # enable wrapping

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
            debug(f"File '{in_file}' exists!")
            if in_file.is_file():
                debug("It's a regular file.")
                history = pd.read_csv(in_file)
        else:
            print(f"File '{in_file}' does not exist.")
    except Exception as e:
        print(f"Error: {e}")


    print(f"\nTrade history for {this_date}")

    # Convert Time column to datetime and sort increasing
    history['Update Time'] = pd.to_datetime(history['Update Time'])
    history = history.sort_values(by='Update Time', ascending=True)

    # history.info() # print summary of dataframe
    # print(len(history), "rows in history")
    # print(history.head()) # print first 5 rows of dataframe

    # filter out all dates except for this_date
    daily_history = history[history['Update Time'].dt.date == pd.to_datetime(this_date).date()].copy()

    if daily_history.empty:
        print("No trades on this date")
        usage()
        exit(1)

    # remove unneded columns; don't want them to appear in the report
    daily_history.drop(['Qty', 'Remaining Qty', 'Limit Price', 'Stop Loss', 'Stop Price', 'Take Profit', 'Expiry', 'Expiry Time', 'Order ID'], axis=1, inplace=True)
    daily_history.sort_values(['Update Time'], inplace=True) # sort trades by increasing time (oldest first)

        ### create columns for aggregation ###

    # create column reflecting negative quantity for sells
    daily_history['Side'] = daily_history['Side'].str.strip() # remove leading/trailing whitespace
    daily_history['net_qty'] = daily_history['Filled Qty'].where(daily_history['Side'] == 'Buy', -daily_history['Filled Qty'])

    # Syntax: keep original value if condition is True; replace it with other value if condition is False
    daily_history['buy_qty'] = daily_history['Filled Qty'].where(daily_history['Side'] == 'Buy', 0)
    daily_history['sell_qty'] = daily_history['Filled Qty'].where(daily_history['Side'] == 'Sell', 0)
    daily_history['buy_price'] = daily_history['Avg Fill Price'].where(daily_history['Side'] == 'Buy', 0)
    daily_history['sell_price'] = daily_history['Avg Fill Price'].where(daily_history['Side'] == 'Sell', 0)
    daily_history['ext_buy_price'] = daily_history['buy_price'] * daily_history['buy_qty']
    daily_history['ext_sell_price'] = daily_history['sell_price'] * daily_history['sell_qty']
    daily_history['fee'] = daily_history['Symbol'].apply(get_fee) * daily_history['Filled Qty']

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
                        total_fee=('fee', 'sum'),
                    )
                    .reset_index())

    net_positions['net_price_chg'] = net_positions['total_sell_price'] - net_positions['total_buy_price']
    net_positions['net_price_chg'] = net_positions['net_price_chg'].round(2) # round to 2 decimal places
    # print("\nAggregate columns:")
    # print(net_positions)

    # convert ticks to dollars
    net_positions['PnL'] = net_positions.apply(lambda row: price_chg_to_dollars(row['Symbol'], row['net_price_chg']), axis=1)
    # apply() is an iterator function of a dataframe; axis=1 means "iterate through all rows" i.e. apply the lambda function to each row
    # "row" is an arbitrary (but conventional) variable name (not a keyword) that identifes a single row passed as the argument to the lambda
    net_positions['PnL'] = net_positions['PnL'] - net_positions['total_fee'] # subtract fees from PnL

    # compute percentage return on margin for each symbol
    net_positions['PnL%'] = net_positions.apply(lambda row: calc_percent_return(row['Symbol'], row['total_buy_qty'], row['PnL']), axis=1)
    net_positions['PnL%'] = net_positions['PnL%'] * 100 # convert decimal to percentage
    net_positions['PnL%'] = net_positions['PnL%'].round(1) # round to 2 decimal places

    print("\nPnL per symbol:")
    print(net_positions)

    # compute total PnL for all symbols
    total_pnl = net_positions['PnL'].sum()
    print(f"\nTotal PnL (including fees): {total_pnl:.2f}")

    # compute total_fees as the sum of the fee column in daily_history
    total_fees = daily_history['fee'].sum()
    
    total_pnl_excluding_fees = total_pnl + total_fees
    print(f"Total PnL (excluding fees): {total_pnl_excluding_fees:.2f}\n")

    # check to ensure all contracts closed
    if (net_positions['net_qty'] != 0).any():
        print("The following symbols have non-zero net quantity:")
        print(net_positions[net_positions['net_qty'] != 0].to_string(index=False))
    else:
        print("All positions are flat (net_qty = 0 for all symbols).")

   # save results to CSV
    out_file = downloads_folder / f"{this_date} tradovate-orders-filled-rpt.csv"
 
    with open(out_file, "w", encoding='utf-8') as f:
        f.write(f"Tradovate trades for {this_date}\n")
        daily_history.to_csv(f, index=False, sep=',', lineterminator='\n')

        f.write(f"\nPnL per symbol\n")
        net_positions.to_csv(f, index=False, sep=',', lineterminator='\n')
        f.write(f"\nTotal PnL:,{total_pnl}\n")
        f.write(f"Total PnL less fees:,{total_pnl_less_fees}\n")

if __name__ == "__main__":
    main()