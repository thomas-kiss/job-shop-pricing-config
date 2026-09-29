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


def run_operation(op: Operation, part: dict, qty: int) -> float:
    def var(label, default, value_type="number"):
        return default

    part_ns = SimpleNamespace(**part)

    scope_dict = {
        "__builtins__": {},
        "part": part_ns,
        "qty": qty,
        "var": var,
    }

    exec(op.code, scope_dict)
    if "PRICE" not in scope_dict:
        raise ScriptError(f'{op.filename} script never set "PRICE"')
    price = scope_dict["PRICE"]
    return price


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

        for op_name in routing:
            op_object = self.operations.get(op_name, "Operation name not found")
            total +=  run_operation(op_object, part, qty)

        return total





