
from kivy.graphics.texture import Texture
import thorvg_cython as tvg


tex = Texture.create(size=(512, 256), colorfmt="rgba")
tex.flip_vertical()

engine = tvg.Engine(threads=4)
canvas = tvg.SwCanvas(512, 256)  # w, h

rect = tvg.Shape()
rect.append_rect(10, 10, 64, 64, 10, 10)  # x, y, w, h, rx, ry
rect.set_fill_color(32, 64, 128, 100)  # r, g, b, a
canvas.add(rect)

canvas.update()
canvas.draw(True)
canvas.sync()

# copy pixels to Kivy texture
tex.blit_buffer(canvas, colorfmt="rgba", bufferfmt="ubyte")