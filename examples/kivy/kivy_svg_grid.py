"""SVG rendered at multiple scales via SvgDataWidget in a GridLayout."""
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
import thorvg_cython as tvg

tvg.Engine(threads=4)

SVG_DATA = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <polygon points="50,5 95,97.5 5,97.5" fill="#E91E63"/>
  <circle cx="50" cy="60" r="20" fill="#FFF" opacity="0.8"/>
</svg>"""


class SvgDataWidget(Image):
    """Kivy Image widget that renders SVG from bytes."""

    def __init__(self, data, width=256, height=256,
                 mimetype="image/svg+xml", **kwargs):
        super().__init__(**kwargs)
        canvas_tvg = tvg.SwCanvas(width, height)

        pic = tvg.Picture()
        pic.load_data(data, mimetype=mimetype)
        pic.set_size(width, height)
        canvas_tvg.add(pic)

        canvas_tvg.update()
        canvas_tvg.draw(True)
        canvas_tvg.sync()

        tex = Texture.create(size=(width, height), colorfmt="rgba")
        tex.flip_vertical()
        tex.blit_buffer(canvas_tvg, colorfmt="rgba", bufferfmt="ubyte")
        self.texture = tex


class SvgGridApp(App):
    def build(self):
        grid = GridLayout(cols=2, padding=10, spacing=10)
        for w, h in [(64, 64), (128, 128), (256, 256), (512, 512)]:
            grid.add_widget(SvgDataWidget(SVG_DATA, w, h))
        return grid


if __name__ == "__main__":
    SvgGridApp().run()
