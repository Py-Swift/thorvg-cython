"""Render inline SVG bytes via a reusable SvgDataWidget."""
from kivy.app import App
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
import thorvg_cython as tvg

tvg.Engine(threads=4)

SVG_DATA = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <circle cx="100" cy="100" r="80" fill="#4CAF50" opacity="0.9"/>
  <circle cx="100" cy="100" r="50" fill="#FFC107"/>
  <rect x="70" y="70" width="60" height="60" rx="8"
        fill="none" stroke="#333" stroke-width="3"/>
</svg>"""


class SvgDataWidget(Image):
    """Kivy Image widget that renders SVG from bytes."""

    def __init__(self, data, width=400, height=400,
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


class InlineSvgApp(App):
    def build(self):
        return SvgDataWidget(SVG_DATA, 400, 400)


if __name__ == "__main__":
    InlineSvgApp().run()
