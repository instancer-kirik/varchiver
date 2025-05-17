local database = {}

function database.enter()
    -- Initialize database scene state
    database.items = db_manager.load().items or {}
    database.selected = 1
    database.scroll = 0
    database.itemsPerPage = 10
end

function database.update(dt)
    -- Handle keyboard navigation
    if lovr.keyboard.isDown('up') then
        database.selected = math.max(1, database.selected - 1)
    elseif lovr.keyboard.isDown('down') then
        database.selected = math.min(#database.items, database.selected + 1)
    end
    
    -- Handle scrolling
    if database.selected < database.scroll + 1 then
        database.scroll = database.selected - 1
    elseif database.selected > database.scroll + database.itemsPerPage then
        database.scroll = database.selected - database.itemsPerPage
    end
end

function database.draw()
    -- Draw title
    lovr.graphics.setColor(1, 1, 1)
    lovr.graphics.print("Item Database", 0, -2, 0, 0.5)
    
    -- Draw items
    local y = -1.5
    for i = database.scroll + 1, math.min(database.scroll + database.itemsPerPage, #database.items) do
        local item = database.items[i]
        if i == database.selected then
            lovr.graphics.setColor(1, 1, 0)
        else
            lovr.graphics.setColor(1, 1, 1)
        end
        
        -- Draw item name
        lovr.graphics.print(item.name, 0, y, 0, 0.3)
        
        -- Draw item details
        lovr.graphics.setColor(0.7, 0.7, 0.7)
        lovr.graphics.print(string.format("Tier: %s", item.tech_tier), 0.5, y, 0, 0.2)
        lovr.graphics.print(string.format("Type: %s", item.energy_type), 1.5, y, 0, 0.2)
        
        y = y + 0.3
    end
    
    -- Draw selected item details
    if database.selected > 0 and database.selected <= #database.items then
        local item = database.items[database.selected]
        y = 1
        
        lovr.graphics.setColor(1, 1, 1)
        lovr.graphics.print("Item Details:", 0, y, 0, 0.3)
        y = y + 0.3
        
        lovr.graphics.print(string.format("Name: %s", item.name), 0, y, 0, 0.2)
        y = y + 0.2
        lovr.graphics.print(string.format("Description: %s", item.description), 0, y, 0, 0.2)
        y = y + 0.2
        lovr.graphics.print(string.format("Tech Tier: %s", item.tech_tier), 0, y, 0, 0.2)
        y = y + 0.2
        lovr.graphics.print(string.format("Energy Type: %s", item.energy_type), 0, y, 0, 0.2)
        y = y + 0.2
        lovr.graphics.print(string.format("Weight: %s", inventory_utils.formatWeight(item)), 0, y, 0, 0.2)
        y = y + 0.2
        lovr.graphics.print(string.format("Volume: %s", inventory_utils.formatVolume(item)), 0, y, 0, 0.2)
        y = y + 0.2
        lovr.graphics.print(string.format("Effects: %s", inventory_utils.getEffectsString(item)), 0, y, 0, 0.2)
    end
end

return database 