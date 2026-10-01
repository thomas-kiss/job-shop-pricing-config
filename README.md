# Job Shop Pricing Configurator

[![CI](https://github.com/thomas-kiss/job-shop-pricing-config/actions/workflows/ci.yml/badge.svg)](https://github.com/thomas-kiss/job-shop-pricing-config/actions/workflows/ci.yml)

A simple, lightweight, configurable pricing engine for a CNC job shop. A shop's quoting rules (work-center rates, material costs, setup and run-time estimates, inspection requirements) are written as small operation scripts and editable tables, and a generic engine runs them to produce a quote for any part at any quantity.

It's modeled on public information about [Paperless Parts](https://www.paperlessparts.com/)' P3L pricing language. This is a personal project, not affiliated with Paperless Parts and not a reproduction of their product. Where the design follows their public SDK or documentation, it's cited in [Design references](#design-references).

**Status:** in progress. The full milling routing (6 operations) quotes 5 real reference parts. Finishing, markups, lathe work, and validation against market prices are next. See the [Roadmap](#roadmap).

## Sample output

`python demo.py` quotes every part at 1, 10, 50, and 100 pieces:

```
NIST FTC-09 Plate
Routing: material_plate, saw, programming, cnc_mill, deburr, inspection

   Qty |        Total
------------------------
     1 |       262.71
    10 |       786.58
    50 |      3114.92
   100 |      6025.34
```

Across all five parts (cost before finishing and markup):

| Part | Material | Total at qty 1 | Per part at qty 100 |
|---|---|---|---|
| FTC-06 Bracket | 304 Stainless | $1,722.19 | $1,395.99 |
| FTC-07 Box | 6061-T6 Aluminum | $1,112.45 | $662.50 |
| FTC-08 Lid | 6061-T6 Aluminum | $537.93 | $273.60 |
| FTC-09 Plate | 6061-T6 Aluminum | $262.71 | $60.25 |
| FTC-10 Housing | 6061-T6 Aluminum, tight tolerance | $444.78 | $56.70 |

Per-part cost falls with quantity because setup, programming, and first-article inspection are charged once per order and spread across the run.

## Contents

- [Why I built this](#why-i-built-this)
- [How it works](#how-it-works)
- [Debugging and validation](#debugging-and-validation)
- [Design references](#design-references)
- [Limitations](#limitations)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Roadmap](#roadmap)
- [Acknowledgements](#acknowledgements)
- [License](#license)

## Why I built this

I wanted to practice the work of a pricing-configuration consultant at a manufacturing software company: learning how a shop prices its work, then turning that into structured, maintainable configuration that someone else can pick up, without changing the platform underneath it.

I come at this from the customer side of a machine shop. I restore vintage two-stroke motorcycles, and I've designed parts and had them made by local machine shops. I wanted to understand what goes into the quotes I've received, and how a quoting platform turns a shop's experience into numbers.

What I practiced along the way:

- **Building a small sandboxed scripting language in Python.** The engine compiles each operation script and runs it with `exec()` against a controlled set of names, then reads the result back out. The script-facing functions (`var`, `lookup`, the workpiece functions) are closures over each quote's data, which keeps the scripts short and readable.
- **Why platforms build their own languages.** Safety on shared infrastructure, variables that become editable fields for estimators, and logic a non-programmer can follow. I compared my design against Paperless Parts' public P3L documentation and changed it where the real platform does something better, for example renaming my output variable to `COST` and adopting their workpiece functions.
- **Job-shop costing.** Setup vs. run time and why per-part cost falls with quantity, material priced by weight from a stock envelope, machinability, roughing and finishing rates, programming time that grows with the number of setups, deburring by surface area, first-article inspection, and tight-tolerance work.
- **Diagnosing pricing problems.** Starting from a symptom ("steel quotes look off"), reasoning about the cause before changing code, and confirming the fix with before-and-after quotes.
- **A professional development workflow.** Feature branches, small commits, pull requests, tagged milestones, pytest, and GitHub Actions running tests and lint on every push, including tracking down two failures that passed locally but broke in CI.
- **Documenting with sources.** Separating what comes from Paperless Parts' public material from what I designed myself, and citing it.

## How it works

### Engine and configuration are separate

[`runtime/engine.py`](runtime/engine.py) is generic. It loads operation scripts, runs them in isolation, looks values up in tables, and adds up the cost of each operation in a part's routing. Everything specific to one shop lives in [`config/coastal/`](config/coastal/) as scripts and tables. Onboarding a second shop means adding a second config folder, with no engine changes.

### The pricing model

Each operation in the milling routing prices one step of the job:

| Operation | What it charges for | Cost drivers |
|---|---|---|
| `material_plate` | Raw stock | Bounding box plus a 0.25 in buffer, material density, cost per pound |
| `saw` | Cutting stock into a blank | Fixed setup, minutes per cut |
| `programming` | CAM programming, once per order | 1.0 hr for the first setup, 0.5 hr for each additional setup |
| `cnc_mill` | Machining | Setup hours per setup; run time from removed volume, surface area, and hole count, scaled by material machinability |
| `deburr` | Hand deburring | Base minutes plus surface area |
| `inspection` | First article and per-part checks | Flat first-article fee, minutes per part and per hole, doubled for tight tolerance |

Rates come from the work-center table, and material properties come from the materials table.

### Operation scripts

Each operation is a short script in [`default_operations/`](config/coastal/default_operations/). A script reads the part (`part.material`, `part.hole_count`, and so on) and the order quantity (`qty`), declares any number an estimator should be able to adjust with `var()`, and sets `COST`, the dollar amount that operation adds to the quote. The milling operation:

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

### Rates and materials live in tables

Work-center rates and material properties are CSV files in [`tables/`](config/coastal/tables/), read by scripts through `lookup(table, key, column)`. Raising the CNC Mill machine rate is a one-cell edit in `work_centers.csv`. Every quote picks it up and no script changes.

### Operations share data through a workpiece

`set_workpiece_value()` and `get_workpiece_value()` pass values from one operation to a later one in the same quote. The material operation sizes the stock once, and the milling operation reads that value instead of recalculating it.

### Why a restricted language

A quoting platform runs many shops' pricing logic on shared infrastructure, so scripts can't be allowed to do everything Python can. Here, scripts run through `exec()` with an empty builtins dictionary, so they have no access to imports, files, or anything beyond the functions the engine hands them. A restricted language also keeps the logic readable to an estimator, and on the real platform each `var()` becomes an editable field in the quoting interface.

## Debugging and validation

Two pricing bugs found and fixed while building the routing:

- **Material machinability was ignored.** The materials table had a machinability column, but the milling script never used it, so every material was priced as if it cut like aluminum. I found it by working back from a simulated customer report that steel quotes looked off, then confirmed the fix by quoting the same plate in aluminum ($262.71) and in steel ($278.97) at quantity 1.
- **Programming hours were divided by 60.** A line in `programming.dsl` treated a value already in hours as if it were minutes, cutting programming cost to a sixtieth of what it should be. I caught it by checking the total by hand against the expected rate times hours.

Tests cover a positive quote total, unit price falling as quantity rises, and a clear error when a script fails to set `COST`. CI runs the tests and `ruff` on every push, and each stage was built on a feature branch and merged by pull request.

## Design references

The naming and structure follow two public Paperless Parts sources:

- **[`part-os/core-python`](https://github.com/part-os/core-python)** (LGPL-3.0), their Python SDK, including a de-identified sample order (`tests/unit/mock_data/order.json`) with real operation names and costing variables.
- **[Operation P3L cheat sheet](https://help.paperlessparts.com/s/article/operation-p3l-cheat-sheet)**, their public P3L reference.

| In this project | Source |
|---|---|
| `COST` as the required output variable | P3L cheat sheet |
| `set_workpiece_value()` / `get_workpiece_value()` | P3L cheat sheet |
| A dot-accessible `part` object with geometry and material fields | P3L cheat sheet (real fields are metric and more general, e.g. `part.size_x`, `part.volume`) |
| `min`, `max`, `abs`, `round` available in scripts | P3L cheat sheet's built-in functions |
| `var()` declared once, outside any `if`/`elif` | P3L cheat sheet: `var()` "cannot be called from within an if/elif/else statement." `inspection.dsl` follows this rule |
| Rates split into `Setup Labor Rate`, `Run Labor Rate`, `Machine Rate` | SDK sample order |
| `Lot Charge` / `Piece Price` for outside finishing | SDK sample order ("Chromate" operation) |
| `Markup Percentage` as a separate operation per cost category | SDK sample order |
| `machinability` as a per-material time multiplier | SDK sample order |

### Simplified stand-ins

Some pieces are my own simpler versions of P3L features:

- **`var(label, default, value_type)`** covers the core idea of the real `var()`, which also takes a description, display options, and a dynamic-variable pattern (`frozen=False`, `.update()`, `.freeze()`) for values computed from the part.
- **`lookup(table, key, column)`** stands in for `table_var()` and `table_lookup()`, which can filter and sort on multiple conditions.
- **`.dsl` files** store each operation's script on disk. On the real platform, scripts are written in a code editor in the web interface.
- **`SETUP_TIME` / `RUNTIME`** are plain variables here. The real platform uses lowercase `setup_time` and `runtime`, declared as dynamic variables that the quoting interface displays directly.

## Limitations

- **Geometry comes from automated analysis.** NIST provides the CAD files. Dimensions, volume, surface area, and hole count were measured from them with a Python/OpenCascade script (built with Claude, Sonnet 5), not yet checked by hand in Fusion. Material, finish, and tolerance for each part are my own assignments.
- **Work-center efficiency isn't applied.** The rate table includes an efficiency factor (80% for the CNC Mill), but no script uses it yet, so milling run times are optimistic.
- **Stock is sized as a solid block** around the part's bounding box, not snapped to standard plate sizes. Mostly-hollow parts like the FTC-06 bracket carry high material cost as a result.
- **Script isolation is runtime-only.** Empty builtins block imports and file access, but nothing checks a script's syntax before it runs, so a loop, for example, isn't rejected.
- **Finishing, markups, and lead time aren't priced yet.** Parts carry a `finish` value, but no operation charges for it.

## Project structure

```
.github/workflows/ci.yml    tests, lint, and format check on every push
runtime/engine.py           generic engine: script loading, isolated execution, lookups, workpiece
config/coastal/
  shop.yaml                 shop settings
  process_templates.yaml    routing: which operations run, in order
  default_operations/       the six operation scripts
  tables/                   work_centers.csv, materials_library.csv, stock_sizes.csv
data/parts.json             five NIST reference parts
tests/test_pricing.py
demo.py                     quotes every part at four quantities
```

## Getting started

Requires Python 3.14.

```bash
git clone https://github.com/thomas-kiss/job-shop-pricing-config.git
cd job-shop-pricing-config
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python demo.py        # quote all five parts
pytest -q             # run tests
ruff check .          # lint
ruff format --check . # formatting
```

Built with Python, PyYAML for configuration files, pytest, ruff, and GitHub Actions.

## Roadmap

- [ ] Expand the test suite: regression tests for both pricing bugs (steel costs more than aluminum; programming cost scales with setup count), `lookup()` error cases, workpiece values passing between operations, tight-tolerance inspection, and every part in `parts.json` quoting without errors
- [ ] Syntax allow-list that rejects disallowed constructs (imports, loops, function definitions) before a script runs
- [ ] Finishing operations (anodize, passivate), markups, minimum order, and lead time
- [ ] Hand-measure part geometry in Fusion and compare against the automated values
- [ ] Validate quotes against Xometry market prices and Fusion CAM cycle times
- [ ] Add CNC turning as a second process, using configuration only
- [ ] Simulate a post-launch change request (for example, a rush fee) delivered as a pull request
- [ ] Export quotes in the SDK's order format and map them to an ERP import
- [ ] Apply work-center efficiency and size stock from standard plate sizes

## Acknowledgements

CAD geometry from the NIST MBE PMI Validation and Conformance Testing Project, fully-toleranced test cases FTC-06 through FTC-10, freely usable with acknowledgement. [Source](https://www.nist.gov/ctl/smart-connected-systems-division/smart-connected-manufacturing-systems-group/mbe-pmi-0).

## License

No license. This is a personal portfolio project, not intended for reuse or distribution.
