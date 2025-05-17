local db_manager = {}
local json = require('json')

-- Initialize the database
function db_manager.init()
    -- Create data directory if it doesn't exist
    if not lovr.filesystem.getDirectoryItems('data') then
        lovr.filesystem.createDirectory('data')
    end
    
    -- Initialize database file if it doesn't exist
    local items = lovr.filesystem.getDirectoryItems('data')
    local has_db = false
    for _, item in ipairs(items) do
        if item == 'inventory.db' then
            has_db = true
            break
        end
    end
    
    if not has_db then
        -- Create empty database structure
        local initial_data = {
            items = {},
            categories = {},
            settings = {
                grid_size = {rows = 8, columns = 8},
                theme = "dark"
            }
        }
        
        -- Save initial database
        local success, err = pcall(function()
            lovr.filesystem.write('data/inventory.db', json.stringify(initial_data))
        end)
        
        if not success then
            print("Error creating database:", err)
        end
    end
end

-- Save data to database
function db_manager.save(data)
    local success, err = pcall(function()
        lovr.filesystem.write('data/inventory.db', json.stringify(data))
    end)
    
    if not success then
        print("Error saving to database:", err)
        return false
    end
    return true
end

-- Load data from database
function db_manager.load()
    local success, data = pcall(function()
        local content = lovr.filesystem.read('data/inventory.db')
        if not content then
            return {
                items = {},
                categories = {},
                settings = {
                    grid_size = {rows = 8, columns = 8},
                    theme = "dark"
                }
            }
        end
        return json.parse(content)
    end)
    
    if not success then
        print("Error loading database:", data)
        return {
            items = {},
            categories = {},
            settings = {
                grid_size = {rows = 8, columns = 8},
                theme = "dark"
            }
        }
    end
    return data
end

return db_manager 