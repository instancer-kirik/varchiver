local inventory_utils = {}

-- Check if an item can be stacked
function inventory_utils.canStack(item)
    return item.inventory_properties and 
           item.inventory_properties.stack_size > 1 and 
           item.inventory_properties.max_stack_size > 1
end

-- Get the maximum stack size for an item
function inventory_utils.getMaxStackSize(item)
    if item.inventory_properties then
        return item.inventory_properties.max_stack_size or 1
    end
    return 1
end

-- Check if an item can be placed in a slot
function inventory_utils.canPlaceInSlot(item, slot)
    if not slot.item then return true end
    if slot.item.id == item.id and inventory_utils.canStack(item) then
        return slot.quantity < inventory_utils.getMaxStackSize(item)
    end
    return false
end

-- Get item color based on tech tier
function inventory_utils.getItemColor(item)
    local tier_colors = {
        ["Tier 1"] = {0.3, 0.8, 0.3},  -- Green
        ["Tier 2"] = {0.3, 0.6, 0.9},  -- Blue
        ["Tier 3"] = {0.6, 0.3, 0.9},  -- Purple
        ["Tier 4"] = {1.0, 0.6, 0.0}   -- Orange
    }
    return tier_colors[item.tech_tier] or {1, 1, 1}
end

-- Get item size in grid units
function inventory_utils.getItemSize(item)
    if item.inventory_properties and item.inventory_properties.slot_size then
        return item.inventory_properties.slot_size[1], item.inventory_properties.slot_size[2]
    end
    return 1, 1
end

-- Format item weight
function inventory_utils.formatWeight(item)
    if item.inventory_properties and item.inventory_properties.weight_kg then
        return string.format("%.1f kg", item.inventory_properties.weight_kg)
    end
    return "N/A"
end

-- Format item volume
function inventory_utils.formatVolume(item)
    if item.inventory_properties and item.inventory_properties.volume_l then
        return string.format("%.1f L", item.inventory_properties.volume_l)
    end
    return "N/A"
end

-- Get item effects as formatted string
function inventory_utils.getEffectsString(item)
    if item.effects then
        return table.concat(item.effects, ", ")
    end
    return "No effects"
end

return inventory_utils 