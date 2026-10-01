# Job Shop Pricing Configurator

**Status:** in progress. Increments 1 and 2 complete (MVP engine + full 6-operation mill routing across 5 real parts). See [Roadmap](#roadmap) for what's next. Tagged `resume-2026-10` as the state of the project when first added to a resume.

A configurable pricing engine for a CNC job shop, built to learn and demonstrate the kind of work a **Technical Consultant / Implementation Engineer** does at a SaaS quoting platform: translating a shop's real pricing rules into a restricted, safe scripting layer, driven by editable configuration rather than hardcoded logic.

It's modeled on public information about [Paperless Parts](https://www.paperlessparts.com/)' P3L pricing language. Note this is not an official or affiliated project, and not a claim to reproduce their real product. Where this project's design matches something confirmed from Paperless Parts' own public SDK and documentation, that's called out explicitly below.

## Table of contents

- [Why this exists](#why-this-exists)
- [How it works](#how-it-works)
- [What's built so far](#whats-built-so-far)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Tech stack](#tech-stack)
- [Roadmap](#roadmap)
- [Acknowledgements](#acknowledgements)
- [License](#license)

## Why this exists

The core job of a pricing-configuration consultant is this: a shop tells you how they price work, and you turn that into maintainable, testable configuration, without touching the underlying platform. This project simulates that end to end, for a fictional shop ("Coastal Precision Machining"), quoting real reference parts.

## How it works

**The pricing engine never changes between shops.** `runtime/engine.py` is generic. it knows how to load scripts, run them safely, and look values up in tables. Everything shop-specific such as rates, materials, routing, and pricing logic reside in `config/coastal/` as data and small scripts. Onboarding a different shop would simply require a new config folder with no changes to the engine.

### The scripting layer

Each operation is a small script (`.dsl` files in `config/coastal/default_operations/`) with a restricted vocabulary: it reads `part.*` and `qty`, calls `var(label, default)` for any number an estimator should be able to adjust, and must set `COST` (the dollar amount that operation contributes to the quote). Here's is the CNC milling operation:

```
SETUP_TIME      = var("First Setup Hours", 1.0) + (part.setup_count - 1) * var("Additional Setup Hours", 0.5)
stock_volume    = get_workpiece_value("stock_volume", 0)
removed         = stock_volume - part.part_volume_in3
run_min         = removed / max(var("Roughing Rate (in3/min)", 1.5), 1) + part.surface_area_in2 / var("Finishing Rate (in2/min)", 8) + part.hole_count * var("Minutes Per Hole", 0.3)
machinability   = lookup("materials_library", part.material, "machinability")
run_min         = run_min * machinability
RUNTIME         = run_min / 60
COST            = SETUP_TIME * var("Setup Labor Rate", lookup("work_centers", "CNC Mill", "setup_labor_rate"), "currency") + RUNTIME * qty * var("Machine Rate", lookup("work_centers", "CNC Mill", "machine_rate"), "currency")
```

The file intentionally reads like a worksheet, not a program. Scripts run through Python's `exec()` with an empty builtins dict, so they can't import modules, open files, or reach anything outside the small set of functions the engine explicitly provides.

### Configuration

Rates and material properties live in CSV tables (`config/coastal/tables/`). A script pulls them with `lookup(table, key, column)`, e.g. `lookup("work_centers", "CNC Mill", "setup_labor_rate")`. Changing a shop's rate requires editing a spreadsheet, not a script.

### Operations share data through a workpiece

`set_workpiece_value()` / `get_workpiece_value()` let one operation pass data to a later one in the same quote e.g. the material-buying operation calculates stock size once, and the milling operation reads that same value instead of recalculating it independently.

### Sourcing: what's confirmed real vs. what I designed myself

Paperless Parts' actual P3L reference documentation is behind a customer login, so I didn't build this against the real syntax directly. Two things I *did* have access to, and used to ground this project's design wherever possible:

- Paperless Parts' public, open-source **Python SDK** ([`part-os/core-python`](https://github.com/part-os/core-python), LGPL-3.0), which includes a real, de-identified sample order (`tests/unit/mock_data/order.json`) showing actual operation names and costing-variable structures from their platform.
- Excerpts of Paperless Parts' own **"Operation P3L" reference documentation**, shared with me directly by a user with customer access. It's not publicly linkable (customer-portal only), so I can't cite a URL for it, but it's the source for several of the naming choices below.

| In this project | Source |
|---|---|
| `COST` as the required output variable | Operation P3L reference (customer docs, not publicly linkable) |
| `set_workpiece_value()` / `get_workpiece_value()` | Operation P3L reference: real function names and mechanism |
| Rates split into `Setup Labor Rate`, `Run Labor Rate`, `Machine Rate` | Public SDK sample order |
| `Lot Charge` / `Piece Price` pattern for outside finishing (e.g. anodize) | Public SDK sample order (a real "Chromate" operation) |
| `Markup Percentage` as its own operation per cost category | Public SDK sample order (real markup values) |
| `machinability` as a per-material time multiplier | A real column in the SDK sample order's material data; I'm the one who wired it into the pricing formula here |
| `var()`, `lookup()`, the `.dsl` extension, `SETUP_TIME`/`RUNTIME` casing | My own design. The real equivalents exist in the Operation P3L reference under different names/signatures, which I chose not to copy exactly, to keep this project clearly its own implementation |

## What's built so far

- **Full mill routing, 6 operations:** material purchasing → sawing → CAM programming → milling → deburring → inspection, each pricing against real, editable rate tables.
- **5 real reference parts** (NIST's public MBE PMI test models) quoting successfully with meaningfully different prices, driven entirely by geometry and material, not special-cased per part.
- **A real scripting safety layer:** scripts execute with empty builtins, no access to imports, file I/O, or anything outside an explicit, small function set.
- **Tests and CI:** `pytest` suite, GitHub Actions running tests and lint on every push.

### Two real bugs found and fixed

- **Missing `machinability` multiplier.** `materials_library.csv` had a machinability column from the start, but the initial milling script did not use it. Every material was priced as if it cut as easily as aluminum. Found by reasoning through a (simulated) customer complaint about steel pricing before touching any code; confirmed by comparing the same part quoted in aluminum vs. steel before and after the fix.
- **A unit-conversion bug in `programming.dsl`.** An unnecessary line divided an already-in-hours value by 60 as if converting minutes to hours, silently shrinking programming cost to a fraction of its real value. Caught by checking the math by hand against expected numbers.

### Limitations 

- **Work-center `efficiency` isn't applied yet.** The tables carry an unused efficiency factor per work center (e.g. the CNC Mill runs at 80% efficiency). Run times are currently slightly optimistic as a result.
- **Material is always priced as a solid block** sized to the part's bounding box. For parts that are mostly hollow, this overstates material cost relative to removed volume.
- **No safety AST checker yet.** The empty-builtins sandbox blocks the obvious escape routes, but doesn't yet restrict *which kinds* of Python syntax a script can contain (loops, for instance, aren't blocked).
- **Finishes (anodize/passivate), markups, and lead time** aren't priced yet. Parts carry a `finish` field, but no operation charges for it.

## Project structure

```
job-shop-pricing-config/
  runtime/
    engine.py               the generic engine: script loading, safe execution, table lookups, workpiece
  config/coastal/
    shop.yaml                shop-level settings
    process_templates.yaml   routing: which operations run, in what order
    default_operations/      the six .dsl pricing scripts
    tables/                  work_centers.csv, materials_library.csv, stock_sizes.csv
  data/
    parts.json               5 real NIST reference parts
  tests/
    test_pricing.py
  demo.py                     prints a quote table for every part, at 4 quantities
```

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

pytest -q          # run the test suite
python demo.py      # quote all 5 parts
ruff check .        # lint
```

## Tech stack

Python 3.14, `pytest`, `ruff`, `PyYAML`. No external dependencies for the pricing engine itself. The restriction to the standard library is deliberate, mirroring the constraint a real sandboxed scripting layer would need.

## Roadmap

- [ ] AST-based safety checker: an allow-list of permitted syntax, checked before a script is ever compiled, not just empty builtins at runtime
- [ ] Markups, finish operations (anodize/passivate), minimum order, and lead time
- [ ] Validation against real market quotes (Xometry) and real CAM cycle times (Fusion360)
- [ ] A second process: CNC turning (lathe) added as a configuration to prove the engine generalizes without code changes.
- [ ] A simulated post-launch change request (e.g. a new rush-order fee), delivered as a pull request against the existing configuration
- [ ] Fix the `efficiency` gap and the solid-block material assumption noted above

## Acknowledgements

CAD geometry from the NIST MBE PMI Validation and Conformance Testing Project (fully-toleranced test cases FTC-06 through FTC-10), freely usable with acknowledgement. [Source](https://www.nist.gov/ctl/smart-connected-systems-division/smart-connected-manufacturing-systems-group/mbe-pmi-0).

## License

No license. This is a personal portfolio project, not intended for reuse or distribution.
