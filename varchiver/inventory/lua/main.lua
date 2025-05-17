-- Inventory System
local inventory_utils = require('inventory_utils')

-- Load required modules
local scene_manager = require('scene_manager')
local db_manager = require('db_manager')

local inventory = {
    items = {},
    selected = nil,
    grid = {
        rows = 8,
        columns = 8,
        slotSize = 64
    },
    hoveredSlot = nil,
    dragItem = nil,
    dragStartSlot = nil
}

-- Initialize the game
function lovr.load()
    -- Initialize graphics
    lovr.graphics.setBackgroundColor(0.1, 0.1, 0.1)
    
    -- Initialize database
    db_manager.init()
    
    -- Register scenes
    scene_manager.register('menu', require('scenes/menu'))
    scene_manager.register('inventory', require('scenes/inventory'))
    scene_manager.register('database', require('scenes/database'))
    scene_manager.register('settings', require('scenes/settings'))
    
    -- Start with menu scene
    scene_manager.switch('menu')
    
    -- Create data directory if it doesn't exist
    if not lovr.filesystem.getDirectoryItems('data') then
        lovr.filesystem.createDirectory('data')
    end
    
    -- Load inventory data
    local success, data = pcall(lovr.filesystem.read, 'data/sample_items.json')
    if success and data then
        local json = require('json')
        inventory.items = json.parse(data).items
        
        -- Save items to database
        local db_data = db_manager.load()
        db_data.items = inventory.items
        db_manager.save(db_data)
    else
        print("Error loading sample items:", data)
    end
    
    -- Initialize inventory slots
    inventory.slots = {}
    for row = 1, inventory.grid.rows do
        inventory.slots[row] = {}
        for col = 1, inventory.grid.columns do
            inventory.slots[row][col] = {
                item = nil,
                quantity = 0
            }
        end
    end
end

-- Helper function to get slot at position
function getSlotAtPosition(x, y)
    local col = math.floor(x / inventory.grid.slotSize) + 1
    local row = math.floor(y / inventory.grid.slotSize) + 1
    if col >= 1 and col <= inventory.grid.columns and row >= 1 and row <= inventory.grid.rows then
        return row, col
    end
    return nil, nil
end

-- Update game state
function lovr.update(dt)
    scene_manager.update(dt)
    
    -- Get mouse position
    local x, y = lovr.system.getMousePosition()
    
    -- Update hovered slot
    local row, col = getSlotAtPosition(x, y)
    inventory.hoveredSlot = row and col and {row = row, col = col} or nil
    
    -- Handle mouse input
    if lovr.system.isMouseDown(1) then
        if not inventory.dragItem and inventory.hoveredSlot then
            local slot = inventory.slots[inventory.hoveredSlot.row][inventory.hoveredSlot.col]
            if slot.item then
                inventory.dragItem = slot.item
                inventory.dragStartSlot = {row = inventory.hoveredSlot.row, col = inventory.hoveredSlot.col}
                slot.item = nil
                slot.quantity = 0
            end
        end
    else
        if inventory.dragItem and inventory.hoveredSlot then
            local slot = inventory.slots[inventory.hoveredSlot.row][inventory.hoveredSlot.col]
            if not slot.item then
                slot.item = inventory.dragItem
                slot.quantity = 1
            end
        end
        inventory.dragItem = nil
        inventory.dragStartSlot = nil
    end
end

-- Draw the game
function lovr.draw()
    scene_manager.draw()
    
    -- Draw inventory grid
    local x, y = 0, 0
    for row = 1, inventory.grid.rows do
        for col = 1, inventory.grid.columns do
            -- Draw slot background
            local slot = inventory.slots[row][col]
            if inventory.hoveredSlot and inventory.hoveredSlot.row == row and inventory.hoveredSlot.col == col then
                lovr.graphics.setColor(0.3, 0.3, 0.3)
            else
                lovr.graphics.setColor(0.2, 0.2, 0.2)
            end
            lovr.graphics.rectangle('fill', x, y, inventory.grid.slotSize, inventory.grid.slotSize)
            
            -- Draw slot border
            lovr.graphics.setColor(0.3, 0.3, 0.3)
            lovr.graphics.rectangle('line', x, y, inventory.grid.slotSize, inventory.grid.slotSize)
            
            -- Draw item if present
            if slot.item then
                local r, g, b = unpack(inventory_utils.getItemColor(slot.item))
                lovr.graphics.setColor(r, g, b)
                -- Draw item icon (placeholder for now)
                lovr.graphics.rectangle('fill', x + 4, y + 4, inventory.grid.slotSize - 8, inventory.grid.slotSize - 8)
                
                -- Draw quantity if more than 1
                if slot.quantity > 1 then
                    lovr.graphics.setColor(1, 1, 1)
                    lovr.graphics.print(slot.quantity, x + 4, y + inventory.grid.slotSize - 20, 0, 0.5)
                end
            end
            
            x = x + inventory.grid.slotSize
        end
        x = 0
        y = y + inventory.grid.slotSize
    end
    
    -- Draw dragged item
    if inventory.dragItem then
        local mx, my = lovr.system.getMousePosition()
        local r, g, b = unpack(inventory_utils.getItemColor(inventory.dragItem))
        lovr.graphics.setColor(r, g, b, 0.7)
        lovr.graphics.rectangle('fill', mx - inventory.grid.slotSize/2, my - inventory.grid.slotSize/2, 
                              inventory.grid.slotSize - 8, inventory.grid.slotSize - 8)
    end
    
    -- Draw item info on hover
    if inventory.hoveredSlot then
        local slot = inventory.slots[inventory.hoveredSlot.row][inventory.hoveredSlot.col]
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
            lovr.graphics.print("Weight: " .. inventory_utils.formatWeight(slot.item), mx + 15, my + y_offset, 0, 0.4)
            y_offset = y_offset + 20
            lovr.graphics.print("Volume: " .. inventory_utils.formatVolume(slot.item), mx + 15, my + y_offset, 0, 0.4)
            y_offset = y_offset + 20
            lovr.graphics.print("Effects: " .. inventory_utils.getEffectsString(slot.item), mx + 15, my + y_offset, 0, 0.4)
        end
    end
end

-- Handle keyboard input
function lovr.keypressed(key)
    if key == 'escape' then
        if scene_manager.current_scene.name ~= 'menu' then
            scene_manager.switch('menu')
        else
            lovr.event.quit()
        end
    end
end 