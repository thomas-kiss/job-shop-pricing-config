import json

from runtime.engine import Shop

shop = Shop("config/coastal")

with open("data/parts.json") as file:
    parts_list = json.load(file)

for part in parts_list:
    part_name = part.get("name")
    print(part_name)

    process_name = part.get("process")
    routing = shop.templates.get(process_name, "Process not found")
    print(f"Routing: {", ".join(routing)}")
    print()

    print(f"{'Qty':>6} | {'Total':>12}")
    print("-" * 24)
    for qty in (1, 10, 50, 100):
        price = shop.quote(part, qty)
        print(f"{qty:>6} | {price:>12.2f}")
    print()
    print()
