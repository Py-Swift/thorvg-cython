import os
from kivy.app import App
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.core.window import Window

Window.clearcolor = [1, 1, 1, 1]

from thorvg_cython import Engine, SwCanvas, Picture, Colorspace


class ThorvgImage(Image):
    def __init__(self, svg_path, **kwargs):
        super().__init__(**kwargs)
        self.svg_path = svg_path

        self.engine = Engine()
        self.engine.init()

        self._render_svg()

    def _render_svg(self):
        w, h = 300, 300
        tvg_canvas = SwCanvas(w, h, int(Colorspace.ABGR8888))

        pic = Picture()
        pic.load(self.svg_path)
        pic.set_size(w, h)

        tvg_canvas.add(pic)
        tvg_canvas.draw()
        tvg_canvas.sync()

        tex = Texture.create(size=(w, h), colorfmt="rgba", bufferfmt="ubyte")

        tex.flip_vertical()

        tex.blit_buffer(tvg_canvas, colorfmt="rgba", bufferfmt="ubyte")

        self.texture = tex


class ThorVGTestApp(App):
    def build(self):
        test_file = "test.svg"
        if not os.path.exists(test_file):
            with open(test_file, "w") as f:
                f.write(
                    """<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="100" cy="100" r="80" fill="#4285F4" />
                  <rect x="60" y="60" width="80" height="80" fill="#DB4437" />
                  <path d="M 60 140 L 140 140 L 100 60 Z" fill="#F4B400" />
                </svg>"""
                )

        return ThorvgImage(svg_path=test_file)


if __name__ == "__main__":
    ThorVGTestApp().run()
