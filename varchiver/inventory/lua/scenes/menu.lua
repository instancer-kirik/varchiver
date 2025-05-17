local menu = {
    options = {},
    selected = 1
}

function menu.enter()
    menu.options = {
        {text = "Inventory", action = function() scene_manager.switch('inventory') end},
        {text = "Database", action = function() scene_manager.switch('database') end},
        {text = "Settings", action = function() scene_manager.switch('settings') end},
        {text = "Exit", action = function() lovr.event.quit() end}
    }
    menu.selected = 1
end

function menu.update(dt)
    -- Handle keyboard navigation
    if lovr.system.isKeyDown('up') then
        menu.selected = menu.selected - 1
        if menu.selected < 1 then menu.selected = #menu.options end
    elseif lovr.system.isKeyDown('down') then
        menu.selected = menu.selected + 1
        if menu.selected > #menu.options then menu.selected = 1 end
    end
    
    -- Handle selection
    if lovr.system.isKeyDown('return') or lovr.system.isKeyDown('space') then
        menu.options[menu.selected].action()
    end
end

function menu.draw()
    -- Draw title
    lovr.graphics.setColor(1, 1, 1)
    lovr.graphics.print("Varchiver", 0, -2, 0, 0.5)
    
    -- Draw menu options
    local y = -1
    for i, option in ipairs(menu.options) do
        if i == menu.selected then
            lovr.graphics.setColor(1, 1, 0)
        else
            lovr.graphics.setColor(1, 1, 1)
        end
        lovr.graphics.print(option.text, 0, y, 0, 0.3)
        y = y + 0.3
    end
end

return menu 