local scene_manager = {
    scenes = {},
    current_scene = nil
}

-- Register a new scene
function scene_manager.register(name, scene)
    scene_manager.scenes[name] = scene
end

-- Switch to a new scene
function scene_manager.switch(name)
    if scene_manager.current_scene and scene_manager.current_scene.exit then
        scene_manager.current_scene.exit()
    end
    
    scene_manager.current_scene = scene_manager.scenes[name]
    
    if scene_manager.current_scene and scene_manager.current_scene.enter then
        scene_manager.current_scene.enter()
    end
end

-- Update current scene
function scene_manager.update(dt)
    if scene_manager.current_scene and scene_manager.current_scene.update then
        scene_manager.current_scene.update(dt)
    end
end

-- Draw current scene
function scene_manager.draw()
    if scene_manager.current_scene and scene_manager.current_scene.draw then
        scene_manager.current_scene.draw()
    end
end

return scene_manager 