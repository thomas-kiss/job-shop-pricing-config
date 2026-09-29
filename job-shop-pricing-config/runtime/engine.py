import csv
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import yaml


class ScriptError(Exception):
    "An operation script is invalid or failed while running"


@dataclass
class Operation:
    name: str
    filename: str
    code: object


def load_operation(path: Path) -> Operation:
    source = path.read_text()
    code = compile(source, path.name, "exec")
    return Operation(path.stem, path.name, code)


def load_tables(folder: Path) -> dict[str, list[dict]]:
    tables = {}
    for path in (folder / "tables").glob("*.csv"):
        with open(path) as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            for row in rows:
                for key in row:
                    try:
                        row[key] = float(row[key])
                    except ValueError:
                        pass
            tables[path.stem] = rows
    return tables


def lookup(tables: dict, table_name: str, key: str, column: str) -> float | str:
    if table_name not in tables:
        known_tables = ", ".join(tables.keys())
        raise ScriptError(f"'{table_name}' not found in '{known_tables}'")
    rows = tables[table_name]
    for row in rows:
        first_col = next(iter(row))
        if row[first_col] == key:
            if column not in row:
                raise ScriptError(f"'{column}' not found in '{table_name}'")
            return row[column]
    raise ScriptError(f"'{key}' not found in table '{table_name}'")


HELPERS = {
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
}


def run_operation(op: Operation, part: dict, qty: int, workpiece: dict) -> float:
    def var(label, default, value_type="number"):
        return default

    def set_workpiece_value(key, value):
        workpiece[key] = value

    def get_workpiece_value(key, default):
        return workpiece.get(key, default)

    part_ns = SimpleNamespace(**part)

    scope_dict = {
        "__builtins__": {},
        "part": part_ns,
        "qty": qty,
        "var": var,
        "set_workpiece_value": set_workpiece_value,
        "get_workpiece_value": get_workpiece_value,
        **HELPERS,
    }

    exec(op.code, scope_dict)  # noqa: S102 — empty __builtins__
    if "COST" not in scope_dict:
        raise ScriptError(f'{op.filename} script never set "COST"')
    cost = scope_dict["COST"]
    return cost


class Shop:
    def __init__(self, folder: str) -> None:
        folder = Path(folder)

        with open(folder / "shop.yaml") as file:
            shop_data = yaml.safe_load(file)
        self.name = shop_data.get("name", "Shop not found")

        with open(folder / "process_templates.yaml") as file:
            process_data = yaml.safe_load(file)
        self.templates = process_data

        self.operations = {}
        for path in (folder / "default_operations").glob("*.dsl"):
            operation = load_operation(path)
            self.operations[operation.name] = operation

    def quote(self, part: dict, qty: int) -> float:
        process_name = part.get("process")
        routing = self.templates.get(process_name, "Process not found")

        total = 0

        workpiece = {}

        for op_name in routing:
            op_object = self.operations.get(op_name, "Operation name not found")
            total += run_operation(op_object, part, qty, workpiece)

        return total
