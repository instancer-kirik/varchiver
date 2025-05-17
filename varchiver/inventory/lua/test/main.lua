function lovr.load()
  print("lovr.load called")
end

function lovr.draw()
  print("lovr.graphics.setColor:", lovr.graphics.setColor)
  if lovr.graphics.setColor then
    lovr.graphics.setColor(1, 0, 0)
    lovr.graphics.print('Hello, LÖVR!', 0, 1, -3)
  else
    print('lovr.graphics.setColor is nil')
  end
end