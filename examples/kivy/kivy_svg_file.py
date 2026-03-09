"""Load an SVG file and display it via a reusable SvgWidget."""
from kivy.app import App
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
import thorvg_cython as tvg

# Initialise the ThorVG engine once at import time
tvg.Engine(threads=4)


class SvgWidget(Image):
    """Kivy Image widget that renders an SVG file via ThorVG."""

    def __init__(self, path, width=512, height=512, **kwargs):
        super().__init__(**kwargs)
        canvas_tvg = tvg.SwCanvas(width, height)

        pic = tvg.Picture()
        pic.load(path)
        pic.set_size(width, height)
        canvas_tvg.add(pic)

        canvas_tvg.update()
        canvas_tvg.draw(True)
        canvas_tvg.sync()

        tex = Texture.create(size=(width, height), colorfmt="rgba")
        tex.flip_vertical()
        tex.blit_buffer(canvas_tvg, colorfmt="rgba", bufferfmt="ubyte")
        self.texture = tex


class SvgApp(App):
    def build(self):
        return SvgWidget("logo.svg", 512, 512)


if __name__ == "__main__":
    SvgApp().run()
