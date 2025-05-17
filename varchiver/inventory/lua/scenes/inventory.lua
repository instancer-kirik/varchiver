local inventory_scene = {
    grid = {
        rows = 8,
        columns = 8,
        slotSize = 64
    },
    slots = {},
    hoveredSlot = nil,
    dragItem = nil,
    dragStartSlot = nil
}

-- Helper function to get slot at position
local function getSlotAtPosition(x, y)
    local col = math.floor(x / inventory_scene.grid.slotSize) + 1
    local row = math.floor(y / inventory_scene.grid.slotSize) + 1
    if col >= 1 and col <= inventory_scene.grid.columns and row >= 1 and row <= inventory_scene.grid.rows then
        return row, col
    end
    return nil, nil
end

function inventory_scene.enter()
    -- Initialize inventory slots
    inventory_scene.slots = {}
    for row = 1, inventory_scene.grid.rows do
        inventory_scene.slots[row] = {}
        for col = 1, inventory_scene.grid.columns do
            inventory_scene.slots[row][col] = {
                item = nil,
                quantity = 0
            }
        end
    end
    
    -- Load player's inventory from database
    local db_data = require('db_manager').load()
    if db_data and db_data.items then
        -- TODO: Load items into slots
    end
end

function inventory_scene.update(dt)
    -- Get mouse position
    local x, y = lovr.system.getMousePosition()
    
    -- Update hovered slot
    local row, col = getSlotAtPosition(x, y)
    inventory_scene.hoveredSlot = row and col and {row = row, col = col} or nil
    
    -- Handle mouse input
    if lovr.system.isMouseDown(1) then
        if not inventory_scene.dragItem and inventory_scene.hoveredSlot then
            local slot = inventory_scene.slots[inventory_scene.hoveredSlot.row][inventory_scene.hoveredSlot.col]
            if slot.item then
                inventory_scene.dragItem = slot.item
                inventory_scene.dragStartSlot = {row = inventory_scene.hoveredSlot.row, col = inventory_scene.hoveredSlot.col}
                slot.item = nil
                slot.quantity = 0
            end
        end
    else
        if inventory_scene.dragItem and inventory_scene.hoveredSlot then
            local slot = inventory_scene.slots[inventory_scene.hoveredSlot.row][inventory_scene.hoveredSlot.col]
            if not slot.item then
                slot.item = inventory_scene.dragItem
                slot.quantity = 1
            end
        end
        inventory_scene.dragItem = nil
        inventory_scene.dragStartSlot = nil
    end
end

function inventory_scene.draw()
    -- Draw inventory grid
    local x, y = 0, 0
    for row = 1, inventory_scene.grid.rows do
        for col = 1, inventory_scene.grid.columns do
            -- Draw slot background
            local slot = inventory_scene.slots[row][col]
            if inventory_scene.hoveredSlot and inventory_scene.hoveredSlot.row == row and inventory_scene.hoveredSlot.col == col then
                lovr.graphics.setColor(0.3, 0.3, 0.3)
            else
                lovr.graphics.setColor(0.2, 0.2, 0.2)
            end
            lovr.graphics.rectangle('fill', x, y, inventory_scene.grid.slotSize, inventory_scene.grid.slotSize)
            
            -- Draw slot border
            lovr.graphics.setColor(0.3, 0.3, 0.3)
            lovr.graphics.rectangle('line', x, y, inventory_scene.grid.slotSize, inventory_scene.grid.slotSize)
            
            -- Draw item if present
            if slot.item then
                local r, g, b = unpack(require('inventory_utils').getItemColor(slot.item))
                lovr.graphics.setColor(r, g, b)
                -- Draw item icon (placeholder for now)
                lovr.graphics.rectangle('fill', x + 4, y + 4, inventory_scene.grid.slotSize - 8, inventory_scene.grid.slotSize - 8)
                
                -- Draw quantity if more than 1
                if slot.quantity > 1 then
                    lovr.graphics.setColor(1, 1, 1)
                    lovr.graphics.print(slot.quantity, x + 4, y + inventory_scene.grid.slotSize - 20, 0, 0.5)
                end
            end
            
            x = x + inventory_scene.grid.slotSize
        end
        x = 0
        y = y + inventory_scene.grid.slotSize
    end
    
    -- Draw dragged item
    if inventory_scene.dragItem then
        local mx, my = lovr.system.getMousePosition()
        local r, g, b = unpack(require('inventory_utils').getItemColor(inventory_scene.dragItem))
        lovr.graphics.setColor(r, g, b, 0.7)
        lovr.graphics.rectangle('fill', mx - inventory_scene.grid.slotSize/2, my - inventory_scene.grid.slotSize/2, 
                              inventory_scene.grid.slotSize - 8, inventory_scene.grid.slotSize - 8)
    end
    
    -- Draw item info on hover
    if inventory_scene.hoveredSlot then
        local slot = inventory_scene.slots[inventory_scene.hoveredSlot.row][inventory_scene.hoveredSlot.col]
        if slot.item then
            local mx, my = lovr.system.getMousePosition()
            lovr.graphics.setColor(0.1, 0.1, 0.1, 0.9)
            lovr.graphics.rectangle('fill', mx + 10, my + 10, 300, 200)
            
            -- Draw item info
            lovr.graphics.setColor(1, 1, 1)
            local y_offset = 15
            lovr.graphics.print(slot.item.name, mx + 15, my + y_offset, 0, 0.5)
            y_offset = y_offset + 20
            lovr.graphics.print(slot.item.description, mx + 15, my + y_offset, 0, 0.4)
            y_offset = y_offset + 30
            
            -- Draw item properties
            lovr.graphics.print("Tech Tier: " .. slot.item.tech_tier, mx + 15, my + y_offset, 0, 0.4)
            y_offset = y_offset + 20
            lovr.graphics.print("Energy Type: " .. slot.item.energy_type, mx + 15, my + y_offset, 0, 0.4)
            y_offset = y_offset + 20
            lovr.graphics.print("Weight: " .. require('inventory_utils').formatWeight(slot.item), mx + 15, my + y_offset, 0, 0.4)
            y_offset = y_offset + 20
            lovr.graphics.print("Volume: " .. require('inventory_utils').formatVolume(slot.item), mx + 15, my + y_offset, 0, 0.4)
            y_offset = y_offset + 20
            lovr.graphics.print("Effects: " .. require('inventory_utils').getEffectsString(slot.item), mx + 15, my + y_offset, 0, 0.4)
        end
    end
end

return inventory_scene 