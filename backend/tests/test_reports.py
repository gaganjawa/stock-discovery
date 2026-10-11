from decimal import Decimal as D
from stock_discovery_analysis.reports import wilson


def test_descriptive_interval_and_zero_sample():
    assert wilson(0,0)['lower'] is None
    interval=wilson(5,10)
    assert abs(interval['lower']-D('.2366'))<D('.0001')
    assert abs(interval['upper']-D('.7634'))<D('.0001')
