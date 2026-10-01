flat_fee        = var("First article fee", 75, "currency")
minutes         = var("Minutes per part checked", 2.0) + var("Minutes per hole checked", 0.05) * part.hole_count
run_rate        = var("Run Labor Rate", lookup("work_centers", "Inspection", "run_labor_rate"), "currency")

if part.tolerance == "tight":
   minutes = minutes * 2

RUNTIME         = minutes / 60
COST            = RUNTIME * qty * run_rate + flat_fee
