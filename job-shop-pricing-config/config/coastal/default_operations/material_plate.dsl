buffer          = var("Material Buffer (in)", 0.25)
STOCK_VOLUME    = (part.length_in + buffer) * (part.width_in + buffer) * (part.height_in + buffer)
density         = var("Density (lb/in3)", lookup("materials_library", part.material, "density"))
POUNDS_PER_PART = STOCK_VOLUME * density
COST            = POUNDS_PER_PART * var("Cost Per Pound", lookup("materials_library", part.material, "cost_per_lb"), "currency") * qty

set_workpiece_value("stock_volume", STOCK_VOLUME)