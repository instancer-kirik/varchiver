local settings = {}

function settings.enter()
    -- Initialize settings scene state
    settings.selected = 1
    settings.options = {
        {name = "Grid Size", value = "8x8", action = function() 
            -- Toggle between different grid sizes
            local sizes = {"8x8", "10x10", "12x12"}
            local current = settings.options[1].value
            local index = 1
            for i, size in ipairs(sizes) do
                if size == current then
                    index = i
                    break
                end
            end
            index = index % #sizes + 1
            settings.options[1].value = sizes[index]
            
            -- Update grid size in database
            local data = db_manager.load()
            data.settings.grid_size = {
                rows = tonumber(sizes[index]:match("(%d+)")),
                columns = tonumber(sizes[index]:match("x(%d+)"))
            }
            db_manager.save(data)
        end},
        {name = "Theme", value = "Dark", action = function()
            -- Toggle between themes
            settings.options[2].value = settings.options[2].value == "Dark" and "Light" or "Dark"
            
            -- Update theme in database
            local data = db_manager.load()
            data.settings.theme = settings.options[2].value:lower()
            db_manager.save(data)
        end},
        {name = "Back", action = function() scene_manager.switch('menu') end}
    }
    
    -- Load current settings
    local data = db_manager.load()
    if data and data.settings then
        settings.options[1].value = string.format("%dx%d", data.settings.grid_size.rows, data.settings.grid_size.columns)
        settings.options[2].value = data.settings.theme:gsub("^%l", string.upper)
    end
end

function settings.update(dt)
    -- Handle keyboard navigation
    if lovr.keyboard.isDown('up') then
        settings.selected = math.max(1, settings.selected - 1)
    elseif lovr.keyboard.isDown('down') then
        settings.selected = math.min(#settings.options, settings.selected + 1)
    end
    
    -- Handle selection
    if lovr.keyboard.isDown('return') then
        settings.options[settings.selected].action()
    end
end

function settings.draw()
    -- Draw title
    lovr.graphics.setColor(1, 1, 1)
    lovr.graphics.print("Settings", 0, -2, 0, 0.5)
    
    -- Draw options
    local y = -1
    for i, option in ipairs(settings.options) do
        if i == settings.selected then
            lovr.graphics.setColor(1, 1, 0)
        else
            lovr.graphics.setColor(1, 1, 1)
        end
        
        -- Draw option name
        lovr.graphics.print(option.name, 0, y, 0, 0.3)
        
        -- Draw option value if it exists
        if option.value then
            lovr.graphics.setColor(0.7, 0.7, 0.7)
            lovr.graphics.print(option.value, 1, y, 0, 0.3)
        end
        
        y = y + 0.3
    end
end

return settings 