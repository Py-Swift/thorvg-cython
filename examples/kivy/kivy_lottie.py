"""Animated Lottie playback via a reusable LottieWidget."""
from kivy.app import App
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
import thorvg_cython as tvg

tvg.Engine(threads=4)


class LottieWidget(Image):
    """Kivy widget that plays a Lottie animation at the given FPS."""

    def __init__(self, path, width=512, height=512, fps=60, **kwargs):
        super().__init__(**kwargs)
        self._canvas_tvg = tvg.SwCanvas(width, height)
        self._w, self._h = width, height

        self._anim = tvg.LottieAnimation()
        pic = self._anim.get_picture()
        pic.load(path)
        pic.set_size(width, height)
        self._canvas_tvg.add(pic)

        _, self._total_frames = self._anim.get_total_frame()
        _, self._duration = self._anim.get_duration()
        self._current_frame = 0.0

        self._tex = Texture.create(size=(width, height), colorfmt="rgba")
        self._tex.flip_vertical()
        self._render()

        Clock.schedule_interval(self._tick, 1.0 / fps)

    def _render(self):
        self._canvas_tvg.update()
        self._canvas_tvg.draw(True)
        self._canvas_tvg.sync()
        self._tex.blit_buffer(
            self._canvas_tvg, colorfmt="rgba", bufferfmt="ubyte")
        self.texture = self._tex

    def _tick(self, dt):
        self._current_frame += (dt / self._duration) * self._total_frames
        if self._current_frame >= self._total_frames:
            self._current_frame = 0.0
        self._anim.set_frame(self._current_frame)
        self._render()


class LottieApp(App):
    def build(self):
        return LottieWidget("animation.json", 512, 512)


if __name__ == "__main__":
    LottieApp().run()
