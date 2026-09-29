SETUP_TIME      = var("First Setup Hours", 1.0) + (part.setup_count - 1) * var("Additional Setup Hours", 0.5)
buffer          = var("Material Buffer (in)", 0.125)
stock           = (part.length_in + buffer) * (part.width_in + buffer) * (part.height_in + buffer)
removed         = stock - part.part_volume_in3
run_min         = removed / var("Roughing Rate (in3/min)", 1.5) + part.surface_area_in2 / var("Finishing Rate (in2/min)", 8) + part.hole_count * var("Minutes Per Hole", 0.3)
RUNTIME         = run_min / 60
PRICE           = SETUP_TIME * var("Setup Labor Rate", 75, "currency") + RUNTIME * qty * var("Machine Rate", 100, "currency")

