minutes         = var("Deburr base Minutes", 1.0) + part.surface_area_in2 / var("Deburr Rate (in2/min)", 40)
RUNTIME         = minutes / 60
COST            = RUNTIME * qty * var("Run Labor Rate", lookup("work_centers", "Deburr", "run_labor_rate"), "currency")
