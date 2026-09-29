buffer          = var("Material Buffer (in)", 0.25)
STOCK_VOLUME    = (part.length_in + buffer) * (part.width_in + buffer) * (part.height_in + buffer)
density         = var("Density (lb/in3)", 0.098)
POUNDS_PER_PART = STOCK_VOLUME * density
COST            = POUNDS_PER_PART * var("Cost Per Pound", 4.50, "currency") * qty