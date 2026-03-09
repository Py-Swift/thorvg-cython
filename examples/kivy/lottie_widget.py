from kivy.uix.widget import Widget
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.uix.image import Image

from kivy.properties import (
    StringProperty,
    ObjectProperty,
    ListProperty,
    BooleanProperty,
    NumericProperty,
    OptionProperty,
    AliasProperty,
    ColorProperty,
)

import thorvg_cython as tvg



class LottieWidget(Widget):

    data = ObjectProperty( None, allownone=True)

    texture = ObjectProperty(None, allownone=True)
    texture_size = ListProperty([0, 0])

    def get_image_ratio(self):
        if self.texture:
            return self.texture.width / float(self.texture.height)
        return 1.0

    image_ratio = AliasProperty(get_image_ratio, bind=('texture',), cache=True)
 
    color = ColorProperty([1, 1, 1, 1])

    allow_stretch = BooleanProperty(False, deprecated=True)

    keep_ratio = BooleanProperty(True, deprecated=True)

    fit_mode = OptionProperty(
        "scale-down", options=["scale-down", "fill", "contain", "cover"]
    )

    keep_data = BooleanProperty(False)

    anim_delay = NumericProperty(0.25)


    def get_norm_image_size(self):
        if not self.texture:
            return list(self.size)

        ratio = self.image_ratio
        w, h = self.size
        tw, th = self.texture.size

        if self.fit_mode == "cover":
            widget_ratio = w / max(1, h)
            if widget_ratio > ratio:
                return [w, (w * th) / tw]
            else:
                return [(h * tw) / th, h]
        elif self.fit_mode == "fill":
            return [w, h]
        elif self.fit_mode == "contain":
            iw = w
        else:
            iw = min(w, tw)

        # calculate the appropriate height
        ih = iw / ratio
        # if the height is too higher, take the height of the container
        # and calculate appropriate width. no need to test further. :)
        if ih > h:
            if self.fit_mode == "contain":
                ih = h
            else:
                ih = min(h, th)
            iw = ih * ratio
        return [iw, ih]

    norm_image_size = AliasProperty(
        get_norm_image_size,
        bind=(
            'texture',
            'size',
            'image_ratio',
            'fit_mode',
        ),
        cache=True,
    )
    '''Normalized image size within the widget box.

    This size will always fit the widget size and will preserve the image
    ratio.

    :attr:`norm_image_size` is an :class:`~kivy.properties.AliasProperty` and
    is read-only.
    '''