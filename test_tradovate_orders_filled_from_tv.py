""" Test functions for Tradovate orders filled from TV. """
import pytest

from tradovate_orders_filled_from_tv import get_fee, price_chg_to_dollars, calc_percent_return

# def test_price_chg_to_dollars():
#     """ Test price_chg_to_dollars function. """
#     assert price_chg_to_dollars("MCLQ6", 0.1) == 10
#     assert price_chg_to_dollars("MGCQ6", 1) == 10
#     assert price_chg_to_dollars("MESQ6", 2) == 10
#     assert price_chg_to_dollars("MNQQ6", 5) == 10
#     assert price_chg_to_dollars("M2KQ6", 2) == 10
#     assert price_chg_to_dollars("MYMQ6", 20) == 10

@pytest.mark.parametrize("symbol, price_chg, dollars",
    [
        ("MCLQ6", 0.1, 10),
        ("MGCQ6", 1, 10),    
        ("MESQ6", 2, 10), 
        ("MNQQ6", 5, 10), 
        ("M2KQ6", 2, 10), 
        ("MYMQ6", 20, 10),
        ("MYM", 0.1, 0), # unrecognized symbol
    ],
)
def test_price_chg_to_dollars(symbol, price_chg, dollars):
    assert price_chg_to_dollars(symbol, price_chg) == dollars


@pytest.mark.parametrize("symbol, fee",
    [
        ("MCLQ6", 0.67),
        ("MGCQ6", 0.67),    
        # ("MESQ6", 10), 
        ("MNQQ6", 0.52), 
        ("M2KQ6", 0.52), 
        # ("MYMQ6", 10),
        ("MYM", 0), # unrecognized symbol
    ],
)
def test_get_fee(symbol, fee):
    assert get_fee(symbol) == fee


@pytest.mark.parametrize("symbol, num_contracts, PnL, pcnt_return",
    [
        ("MESQ6", 1, 100, 0.02), 
        ("MNQQ6", 1, 100, 0.01), 
        ("M2KQ6", 1, 100, 0.02), 
        ("MYMQ6", 1, 100, 0.02),
        ("MCLQ6", 1, 100, 0.01),
        ("CLQ6", 1, 100, 0.1),
        ("MGCQ6", 1, 100, 0.005),
        ("MGCQ6", 10, 100, 0.005),
        ("MYM", 1, 1, 0), # unrecognized symbol
        ("MGCQ6", 0, 100, 0), # zero contracts = zero return
        ("MGCQ6", 1, 0, 0), # zero PnL = zero return
    ],
)
def test_calc_percent_return(symbol, num_contracts, PnL, pcnt_return):
    assert calc_percent_return(symbol, num_contracts, PnL) == pcnt_return
