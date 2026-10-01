"""Stand-in P3L runtime: loads a shop's config and runs its operation scripts."""

import csv
from dataclasses import dataclass
from pathlib import Path
from types import CodeType, SimpleNamespace

import yaml


class ScriptError(Exception):
    """An operation script is invalid or failed while running."""


@dataclass
class Operation:
    """A compiled operation script, ready to run."""

    name: str
    filename: str
    code: CodeType


def load_operation(path: Path) -> Operation:
    """Compile a .dsl script into an Operation."""
    source = path.read_text()
    code = compile(source, path.name, "exec")
    return Operation(path.stem, path.name, code)


type Tables = dict[str, list[dict]]


def load_tables(folder: Path) -> Tables:
    """Load each CSV in folder/tables, converting numeric cells to floats."""
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


def lookup(tables: Tables, table_name: str, key: str, column: str) -> float | str:
    """Return `column` from the row whose first column equals `key`.

    Raises ScriptError if the table, row, or column is missing.
    """
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


def run_operation(
    op: Operation, part: dict, qty: int, workpiece: dict[str, float], tables: Tables
) -> float:
    """Run one operation script and return the COST it sets.

    Values saved with set_workpiece_value stay in `workpiece` for later
    operations to read.

    Raises ScriptError if the script does not set COST to a number.
    """

    def var(label, default, value_type="number"):
        return default

    def set_workpiece_value(key, value):
        workpiece[key] = value

    def get_workpiece_value(key, default):
        return workpiece.get(key, default)

    def script_lookup(table_name, key, column):
        return lookup(tables, table_name, key, column)

    part_ns = SimpleNamespace(**part)

    scope_dict = {
        "__builtins__": {},
        "part": part_ns,
        "qty": qty,
        "var": var,
        "set_workpiece_value": set_workpiece_value,
        "get_workpiece_value": get_workpiece_value,
        "lookup": script_lookup,
        **HELPERS,
    }

    exec(op.code, scope_dict)  # noqa: S102 — empty __builtins__
    if "COST" not in scope_dict:
        raise ScriptError(f'{op.filename} script never set "COST"')
    cost = scope_dict["COST"]
    if not isinstance(cost, (int, float)):
        raise ScriptError(
            f'{op.filename} set "COST" to {cost!r}, which is not a number'
        )
    return float(cost)


class Shop:
    """A shop's pricing configuration, loaded from its config folder."""

    def __init__(self, folder: str | Path) -> None:
        folder_path = Path(folder)

        with open(folder_path / "shop.yaml") as file:
            shop_data = yaml.safe_load(file)
        self.name = shop_data.get("name", "Shop not found")

        with open(folder_path / "process_templates.yaml") as file:
            process_data = yaml.safe_load(file)
        self.templates = process_data

        self.tables = load_tables(folder_path)

        self.operations = {}
        for path in (folder_path / "default_operations").glob("*.dsl"):
            operation = load_operation(path)
            self.operations[operation.name] = operation

    def quote(self, part: dict, qty: int) -> float:
        """Price `qty` of a part by running each operation in its routing."""
        process_name = part.get("process")
        routing = self.templates.get(process_name, "Process not found")

        total = 0.0

        workpiece: dict[str, float] = {}

        for op_name in routing:
            op_object = self.operations.get(op_name, "Operation name not found")
            total += run_operation(op_object, part, qty, workpiece, self.tables)

        return total
