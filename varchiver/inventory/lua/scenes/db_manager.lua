local db_manager = {
    items = {},
    player_inventory = {},
    save_file = "save_data.json"
}

-- Load all items from JSON
function db_manager.loadItems()
    local success, data = pcall(lovr.filesystem.read, 'data/sample_items_big.json')
    if success then
        -- Use our local JSON module
        local json = require('json')
        db_manager.items = json.parse(data).items
        -- Create lookup table for faster access
        db_manager.items_by_id = {}
        for _, item in ipairs(db_manager.items) do
            db_manager.items_by_id[item.id] = item
        end
    end
end

-- Get item by ID
function db_manager.getItem(id)
    return db_manager.items_by_id[id]
end

-- Get all items
function db_manager.getAllItems()
    return db_manager.items
end

-- Get items by category
function db_manager.getItemsByCategory(category)
    local result = {}
    for _, item in ipairs(db_manager.items) do
        if item.category == category then
            table.insert(result, item)
        end
    end
    return result
end

-- Get items by tech tier
function db_manager.getItemsByTier(tier)
    local result = {}
    for _, item in ipairs(db_manager.items) do
        if item.tech_tier == tier then
            table.insert(result, item)
        end
    end
    return result
end

-- Save player inventory
function db_manager.saveInventory()
    local data = {
        inventory = db_manager.player_inventory,
        timestamp = os.time()
    }
    -- Use our local JSON module
    local json = require('json')
    local json_str = json.stringify(data)
    lovr.filesystem.write(db_manager.save_file, json_str)
end

-- Load player inventory
function db_manager.loadInventory()
    local success, data = pcall(lovr.filesystem.read, db_manager.save_file)
    if success and data then
        -- Use our local JSON module
        local json = require('json')
        local save_data = json.parse(data)
        db_manager.player_inventory = save_data.inventory or {}
    else
        -- Initialize empty inventory if file doesn't exist
        db_manager.player_inventory = {}
    end
end

-- Add item to player inventory
function db_manager.addItemToInventory(item_id, quantity)
    quantity = quantity or 1
    if not db_manager.player_inventory[item_id] then
        db_manager.player_inventory[item_id] = 0
    end
    db_manager.player_inventory[item_id] = db_manager.player_inventory[item_id] + quantity
    db_manager.saveInventory()
end

-- Remove item from player inventory
function db_manager.removeItemFromInventory(item_id, quantity)
    quantity = quantity or 1
    if db_manager.player_inventory[item_id] then
        db_manager.player_inventory[item_id] = db_manager.player_inventory[item_id] - quantity
        if db_manager.player_inventory[item_id] <= 0 then
            db_manager.player_inventory[item_id] = nil
        end
        db_manager.saveInventory()
        return true
    end
    return false
end

-- Get player inventory
function db_manager.getPlayerInventory()
    local result = {}
    for item_id, quantity in pairs(db_manager.player_inventory) do
        local item = db_manager.getItem(item_id)
        if item then
            table.insert(result, {
                item = item,
                quantity = quantity
            })
        end
    end
    return result
end

-- Initialize database
function db_manager.init()
    db_manager.loadItems()
    db_manager.loadInventory()
end

return db_manager 