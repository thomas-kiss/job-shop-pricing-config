SETUP_TIME      = var("First Setup Hours", 1.0) + (part.setup_count - 1) * var("Additional Setup Hours", 0.5)
stock_volume    = get_workpiece_value("stock_volume", 0)
removed         = stock_volume - part.part_volume_in3
run_min         = removed / max(var("Roughing Rate (in3/min)", 1.5), 1) + part.surface_area_in2 / var("Finishing Rate (in2/min)", 8) + part.hole_count * var("Minutes Per Hole", 0.3)
RUNTIME         = run_min / 60
COST            = SETUP_TIME * var("Setup Labor Rate", lookup("work_centers", "CNC Mill", "setup_labor_rate"), "currency") + RUNTIME * qty * var("Machine Rate", lookup("work_centers", "CNC Mill", "machine_rate"), "currency")