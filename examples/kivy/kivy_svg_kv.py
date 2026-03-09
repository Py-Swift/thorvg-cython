"""SVG file rendered to a Kivy widget using KV language + canvas Rectangle texture binding."""
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.graphics.texture import Texture
import thorvg_cython as tvg

tvg.Engine(threads=4)

Builder.load_string("""
<SvgCanvasWidget>:
    canvas:
        Rectangle:
            texture: self.svg_texture
            pos: self.pos
            size: self.size
""")


class SvgCanvasWidget(Widget):
    """Widget that renders SVG into a texture bound to a canvas Rectangle.

    The KV rule binds the Rectangle's texture/pos/size to this widget,
    so it automatically repositions and resizes with the layout.
    """
    svg_texture = ObjectProperty(None, allownone=True)

    def __init__(self, path, tex_width=512, tex_height=512, **kwargs):
        super().__init__(**kwargs)
        canvas_tvg = tvg.SwCanvas(tex_width, tex_height)

        pic = tvg.Picture()
        pic.load(path)
        pic.set_size(tex_width, tex_height)
        canvas_tvg.add(pic)

        canvas_tvg.update()
        canvas_tvg.draw(True)
        canvas_tvg.sync()

        tex = Texture.create(size=(tex_width, tex_height), colorfmt="rgba")
        tex.flip_vertical()
        tex.blit_buffer(canvas_tvg, colorfmt="rgba", bufferfmt="ubyte")
        self.svg_texture = tex


class SvgKvApp(App):
    def build(self):
        return SvgCanvasWidget("logo.svg", tex_width=512, tex_height=512)


if __name__ == "__main__":
    SvgKvApp().run()
