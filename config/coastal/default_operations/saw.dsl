SETUP_TIME      = var("Saw Setup Hours", 0.1)
cut_min         = var("Saw Minutes Per Cut", 1.5) * var("Cuts per Part", 1)
RUNTIME         = cut_min / 60
COST            = SETUP_TIME * var("Setup Labor Rate", lookup("work_centers", "Saw", "setup_labor_rate"), "currency") + RUNTIME * qty * var("Machine Rate", lookup("work_centers", "Saw", "machine_rate"), "currency")