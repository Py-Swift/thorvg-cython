"""Overlay SVG icons with transforms via a reusable SvgSceneWidget."""
from kivy.app import App
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
import thorvg_cython as tvg

tvg.Engine(threads=4)

ICON_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path fill="#2196F3" d="M12 2L2 7l10 5 10-5-10-5z"/>
  <path fill="#1976D2" d="M2 17l10 5 10-5M2 12l10 5 10-5"/>
</svg>"""


class SvgSceneWidget(Image):
    """Renders multiple transformed SVG icons onto a single texture."""

    def __init__(self, width=512, height=512, **kwargs):
        super().__init__(**kwargs)
        canvas_tvg = tvg.SwCanvas(width, height)

        # Background
        bg = tvg.Shape()
        bg.append_rect(0, 0, width, height, 0, 0)
        bg.set_fill_color(240, 240, 240, 255)
        canvas_tvg.add(bg)

        # Place the same SVG icon at different positions / transforms
        for x, y, sc, rot in [
            (50, 50, 1.0, 0),
            (200, 50, 2.0, 0),
            (50, 250, 1.5, 45),
            (250, 250, 3.0, -30),
        ]:
            pic = tvg.Picture()
            pic.load_data(ICON_SVG, mimetype="image/svg+xml")
            pic.set_size(64, 64)
            pic.translate(x, y)
            pic.scale(sc)
            if rot:
                pic.rotate(rot)
            canvas_tvg.add(pic)

        canvas_tvg.update()
        canvas_tvg.draw(True)
        canvas_tvg.sync()

        tex = Texture.create(size=(width, height), colorfmt="rgba")
        tex.flip_vertical()
        tex.blit_buffer(canvas_tvg, colorfmt="rgba", bufferfmt="ubyte")
        self.texture = tex


class SvgTransformApp(App):
    def build(self):
        return SvgSceneWidget(512, 512)


if __name__ == "__main__":
    SvgTransformApp().run()
