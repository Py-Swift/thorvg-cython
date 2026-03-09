import os
import json
from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.clock import Clock

Window.clearcolor = [1, 1, 1, 1]

from thorvg_cython import Engine, SwCanvas, Colorspace, Animation


class ThorvgLottie(Image):
    def __init__(self, lottie_path, **kwargs):
        super().__init__(**kwargs)
        self.lottie_path = lottie_path

        self.engine = Engine()
        self.engine.init()

        self.w, self.h = 300, 300
        self.tvg_canvas = SwCanvas(self.w, self.h, int(Colorspace.ABGR8888))

        self.anim = Animation()

        self.pic = self.anim.get_picture()

        self.pic.load(self.lottie_path)
        self.pic.set_size(self.w, self.h)

        self.total_frames = self.anim.get_total_frame()[1]
        self.current_frame = 0

        self.tvg_canvas.add(self.pic)

        self.texture = Texture.create(
            size=(self.w, self.h), colorfmt="rgba", bufferfmt="ubyte"
        )
        self.texture.flip_vertical()

        Clock.schedule_interval(self._update_frame, 1.0 / 60.0)

    def _update_frame(self, dt):
        if self.total_frames <= 0:
            return

        self.current_frame = (self.current_frame + 1) % self.total_frames

        self.anim.set_frame(self.current_frame)

        self.tvg_canvas.update()
        self.tvg_canvas.draw()
        self.tvg_canvas.sync()

        self.texture.blit_buffer(self.tvg_canvas, colorfmt="rgba", bufferfmt="ubyte")

        self.canvas.ask_update()


class ThorVGTestApp(App):
    def build(self):
        test_file = os.path.join(self.directory, "ok_lottie.json")

        if not os.path.exists(test_file):
            lottie_data = {
                "v": "5.5.2",
                "fr": 60,
                "ip": 0,
                "op": 60,
                "w": 300,
                "h": 300,
                "nm": "Test",
                "ddd": 0,
                "assets": [],
                "layers": [
                    {
                        "ddd": 0,
                        "ind": 1,
                        "ty": 4,
                        "nm": "Shape",
                        "sr": 1,
                        "ks": {
                            "o": {"a": 0, "k": 100},
                            "r": {"a": 0, "k": 0},
                            "p": {"a": 0, "k": [150, 150, 0]},
                            "a": {"a": 0, "k": [0, 0, 0]},
                            "s": {"a": 0, "k": [100, 100, 100]},
                        },
                        "ao": 0,
                        "shapes": [
                            {
                                "ty": "gr",
                                "it": [
                                    {
                                        "ty": "rc",
                                        "d": 1,
                                        "s": {"a": 0, "k": [100, 100]},
                                        "p": {"a": 0, "k": [0, 0]},
                                        "r": {"a": 0, "k": 0},
                                        "nm": "Rect",
                                        "hd": False,
                                    },
                                    {
                                        "ty": "fl",
                                        "c": {"a": 0, "k": [1, 0, 0, 1]},
                                        "o": {"a": 0, "k": 100},
                                        "r": 1,
                                        "bm": 0,
                                        "nm": "Fill",
                                        "hd": False,
                                    },
                                    {
                                        "ty": "tr",
                                        "p": {"a": 0, "k": [0, 0]},
                                        "a": {"a": 0, "k": [0, 0]},
                                        "s": {"a": 0, "k": [100, 100]},
                                        "r": {
                                            "a": 1,
                                            "k": [
                                                {
                                                    "i": {"x": [0.833], "y": [0.833]},
                                                    "o": {"x": [0.167], "y": [0.167]},
                                                    "t": 0,
                                                    "s": [0],
                                                },
                                                {"t": 60, "s": [360]},
                                            ],
                                        },
                                        "o": {"a": 0, "k": 100},
                                        "sk": {"a": 0, "k": 0},
                                        "sa": {"a": 0, "k": 0},
                                        "nm": "Transform",
                                    },
                                ],
                                "nm": "Group",
                                "np": 3,
                                "cix": 2,
                                "bm": 0,
                                "ix": 1,
                                "hd": False,
                            }
                        ],
                        "ip": 0,
                        "op": 60,
                        "st": 0,
                        "bm": 0,
                    }
                ],
            }
            with open(test_file, "w") as f:
                json.dump(lottie_data, f)

        layout = BoxLayout()
        layout.add_widget(ThorvgLottie(lottie_path=test_file))
        layout.add_widget(ThorvgLottie(lottie_path=test_file))
        layout.add_widget(ThorvgLottie(lottie_path=test_file))
        layout.add_widget(ThorvgLottie(lottie_path=test_file))

        return layout


if __name__ == "__main__":
    ThorVGTestApp().run()
