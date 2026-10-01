import pytest

from runtime.engine import Operation, ScriptError, Shop, run_operation


def test_quote_returns_positive_total():
    shop = Shop("config/coastal")
    part = {
        "part_number": "FTC-09",
        "name": "NIST FTC-09 Plate",
        "process": "mill",
        "material": "6061-T6 Aluminum",
        "finish": "none",
        "tolerance": "standard",
        "length_in": 11.0,
        "width_in": 7.5,
        "height_in": 0.12,
        "part_volume_in3": 8.33,
        "surface_area_in2": 149.8,
        "hole_count": 29,
        "setup_count": 1,
    }
    total = shop.quote(part, 1)
    assert total > 0


def test_unit_price_drops_as_qty_rises():
    shop = Shop("config/coastal")
    part = {
        "part_number": "FTC-09",
        "name": "NIST FTC-09 Plate",
        "process": "mill",
        "material": "6061-T6 Aluminum",
        "finish": "none",
        "tolerance": "standard",
        "length_in": 11.0,
        "width_in": 7.5,
        "height_in": 0.12,
        "part_volume_in3": 8.33,
        "surface_area_in2": 149.8,
        "hole_count": 29,
        "setup_count": 1,
    }
    total_qty_1 = shop.quote(part, 1)
    total_qty_100 = shop.quote(part, 100)
    assert (total_qty_1 / 1) > (total_qty_100 / 100)


def test_missing_cost_raises_script_error():
    part = {
        "part_number": "FTC-09",
        "name": "NIST FTC-09 Plate",
        "process": "mill",
        "material": "6061-T6 Aluminum",
        "finish": "none",
        "tolerance": "standard",
        "length_in": 11.0,
        "width_in": 7.5,
        "height_in": 0.12,
        "part_volume_in3": 8.33,
        "surface_area_in2": 149.8,
        "hole_count": 29,
        "setup_count": 1,
    }
    missing_cost = compile("x=5", "broken.dsl", "exec")
    broken_op = Operation("broken", "broken.dsl", missing_cost)
    with pytest.raises(ScriptError):
        run_operation(broken_op, part, 1, {}, {})
