function lovr.conf(t)
    -- Window configuration
    t.window.title = "Inventory Interface"
    t.window.width = 1280
    t.window.height = 720
    t.window.resizable = true
    t.window.vsync = true
    t.window.msaa = 4  -- Add anti-aliasing
    
    -- Enable modules we'll need
    t.modules.audio = true
    t.modules.data = true
    t.modules.event = true
    t.modules.graphics = true
    t.modules.headset = false  -- Disable VR features for now
    t.modules.math = true
    t.modules.physics = true
    t.modules.system = true
    t.modules.timer = true
    t.modules.window = true
    
    -- Graphics settings
    t.graphics.debug = true  -- Enable debug mode for more information
end 