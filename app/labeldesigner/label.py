from enum import Enum, auto
from qrcode import QRCode, constants
from PIL import Image, ImageDraw, ImageFont


class LabelContent(Enum):
    TEXT_ONLY = auto()
    QRCODE_ONLY = auto()
    TEXT_QRCODE = auto()
    IMAGE_BW = auto()
    IMAGE_GRAYSCALE = auto()


class LabelOrientation(Enum):
    STANDARD = auto()
    ROTATED = auto()


class LabelType(Enum):
    ENDLESS_LABEL = auto()
    DIE_CUT_LABEL = auto()
    ROUND_DIE_CUT_LABEL = auto()


class TextAlign(Enum):
    LEFT = 'left'
    CENTER = 'center'
    RIGHT = 'right'


# Smallest font size the auto-fit search is allowed to fall back to. Below this
# the print is unreadable anyway, so we stop shrinking and let the text clip.
FONT_SIZE_MIN = 4


class SimpleLabel:
    qr_correction_mapping = {
        'L': constants.ERROR_CORRECT_L,
        'M': constants.ERROR_CORRECT_M,
        'Q': constants.ERROR_CORRECT_Q,
        'H': constants.ERROR_CORRECT_H
    }

    def __init__(
            self,
            width=0,
            height=0,
            label_content=LabelContent.TEXT_ONLY,
            label_orientation=LabelOrientation.STANDARD,
            label_type=LabelType.ENDLESS_LABEL,
            # Left, Right, Top, Bottom, each as a fraction of the font size
            label_margin=(0, 0, 0, 0),
            fore_color=(0, 0, 0),  # Red, Green, Blue
            text='',
            text_align=TextAlign.CENTER,
            qr_size=10,
            qr_correction='L',
            image_mode='grayscale',
            image=None,
            font_path='',
            font_size=70,
            font_size_auto=False,
            line_spacing=100):
        self._width = width
        self._height = height
        self.label_content = label_content
        self.label_orientation = label_orientation
        self.label_type = label_type
        self._label_margin = label_margin
        self._fore_color = fore_color
        self.text = text
        self._text_align = text_align
        self._qr_size = qr_size
        self.qr_correction = qr_correction
        self._image = image
        self._font_path = font_path
        self._font_size = font_size
        self._font_size_auto = font_size_auto
        self._line_spacing = line_spacing
        # Size actually used by the last generate(); equals _font_size unless
        # auto-fit shrank it.
        self._effective_font_size = font_size

    @property
    def label_content(self):
        return self._label_content

    @label_content.setter
    def label_content(self, value):
        self._label_content = value

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value

    @property
    def qr_correction(self):
        for key, val in self.qr_correction_mapping:
            if val == self._qr_correction:
                return key

    @qr_correction.setter
    def qr_correction(self, value):
        self._qr_correction = self.qr_correction_mapping.get(
            value, constants.ERROR_CORRECT_L)

    @property
    def label_orientation(self):
        return self._label_orientation

    @label_orientation.setter
    def label_orientation(self, value):
        self._label_orientation = value

    @property
    def label_type(self):
        return self._label_type

    @label_type.setter
    def label_type(self, value):
        self._label_type = value

    @property
    def effective_font_size(self):
        """Font size used by the most recent generate() call."""
        return self._effective_font_size

    def generate(self):
        if self._label_content in (LabelContent.QRCODE_ONLY, LabelContent.TEXT_QRCODE):
            img = self._generate_qr()
        elif self._label_content in (LabelContent.IMAGE_BW, LabelContent.IMAGE_GRAYSCALE):
            img = self._image
        else:
            img = None

        if img is not None:
            img_width, img_height = img.size
        else:
            img_width, img_height = (0, 0)

        has_text = self._label_content in (
            LabelContent.TEXT_ONLY, LabelContent.TEXT_QRCODE)

        if has_text and self._font_size_auto:
            font_size = self._fit_font_size(img_width, img_height)
        else:
            font_size = self._font_size
        self._effective_font_size = font_size

        if has_text:
            textsize = self._get_text_size(font_size)
        else:
            textsize = (0, 0, 0, 0)

        width, height = self._width, self._height
        margin_left, margin_right, margin_top, margin_bottom = self._margins(
            font_size)

        if self._label_orientation == LabelOrientation.STANDARD:
            if self._label_type in (LabelType.ENDLESS_LABEL,):
                height = img_height + textsize[3] - textsize[1] + margin_top + margin_bottom
        elif self._label_orientation == LabelOrientation.ROTATED:
            if self._label_type in (LabelType.ENDLESS_LABEL,):
                width = img_width + textsize[2] + margin_left + margin_right

        if self._label_orientation == LabelOrientation.STANDARD:
            if self._label_type in (LabelType.DIE_CUT_LABEL, LabelType.ROUND_DIE_CUT_LABEL):
                vertical_offset_text = (height - img_height - textsize[3])//2
                vertical_offset_text += (margin_top - margin_bottom)//2
            else:
                vertical_offset_text = margin_top

            vertical_offset_text += img_height
            horizontal_offset_text = max((width - textsize[2])//2, 0)
            horizontal_offset_image = (width - img_width)//2
            vertical_offset_image = margin_top

        elif self._label_orientation == LabelOrientation.ROTATED:
            vertical_offset_text = (height - textsize[3])//2
            vertical_offset_text += (margin_top - margin_bottom)//2
            if self._label_type in (LabelType.DIE_CUT_LABEL, LabelType.ROUND_DIE_CUT_LABEL):
                horizontal_offset_text = max((width - img_width - textsize[2])//2, 0)
            else:
                horizontal_offset_text = margin_left
            horizontal_offset_text += img_width
            horizontal_offset_image = margin_left
            vertical_offset_image = (height - img_height)//2

        text_offset = horizontal_offset_text, vertical_offset_text - textsize[1]
        image_offset = horizontal_offset_image, vertical_offset_image

        imgResult = Image.new('RGB', (int(width), int(height)), 'white')

        if img is not None:
            imgResult.paste(img, image_offset)

        if has_text:
            draw = ImageDraw.Draw(imgResult)
            draw.multiline_text(
                text_offset,
                self._prepare_text(self._text),
                self._fore_color,
                font=self._get_font(font_size),
                align=self._text_align,
                spacing=self._line_spacing_px(font_size))

        return imgResult

    def _generate_qr(self):
        qr = QRCode(
            version=1,
            error_correction=self._qr_correction,
            box_size=self._qr_size,
            border=0,
        )
        qr.add_data(self._text.encode("utf-8-sig"))
        qr.make(fit=True)
        qr_img = qr.make_image(
            fill_color='red' if (255, 0, 0) == self._fore_color else 'black',
            back_color="white")
        return qr_img

    def _fit_font_size(self, img_width, img_height):
        """Largest font size <= the requested one whose text still fits the
        label's fixed dimensions.

        Binary search: everything that consumes space (glyphs, line spacing and
        the margins, which are a fraction of the font size) grows monotonically
        with the font size, so 'fits' flips exactly once over the range.
        """
        low, high = FONT_SIZE_MIN, max(FONT_SIZE_MIN, self._font_size)

        if self._fits(high, img_width, img_height):
            return high

        while low < high:
            mid = (low + high + 1) // 2
            if self._fits(mid, img_width, img_height):
                low = mid
            else:
                high = mid - 1

        return low

    def _fits(self, font_size, img_width, img_height):
        """True if the text rendered at font_size stays inside every label
        dimension that is fixed.

        Endless labels grow along one axis, so only the other one constrains
        us: standard orientation grows in height, rotated grows in width.
        """
        margin_left, margin_right, margin_top, margin_bottom = self._margins(
            font_size)
        bbox = self._get_text_size(font_size)
        text_width = bbox[2]
        text_height = bbox[3] - bbox[1]

        endless = self._label_type == LabelType.ENDLESS_LABEL

        if self._label_orientation == LabelOrientation.STANDARD:
            # Image sits above the text, and left/right margins are unused.
            width_constrained = True
            height_constrained = not endless
            needed_width = max(text_width, img_width)
            needed_height = img_height + text_height + margin_top + margin_bottom
        else:
            # Image sits left of the text, both vertically centered.
            width_constrained = not endless
            height_constrained = True
            needed_width = img_width + text_width + margin_left + margin_right
            needed_height = max(
                img_height, text_height + margin_top + margin_bottom)

        if width_constrained and needed_width > self._width:
            return False
        if height_constrained and needed_height > self._height:
            return False
        return True

    def _margins(self, font_size):
        """Margins in pixels; they are stored as a fraction of the font size."""
        return tuple(int(font_size * fraction) for fraction in self._label_margin)

    def _line_spacing_px(self, font_size):
        return int(font_size*((self._line_spacing - 100) / 100))

    def _get_text_size(self, font_size):
        font = self._get_font(font_size)
        img = Image.new('L', (20, 20), 'white')
        draw = ImageDraw.Draw(img)
        return draw.multiline_textbbox(
            (0, 0),
            self._prepare_text(self._text),
            font=font,
            align=self._text_align,
            spacing=self._line_spacing_px(font_size))

    @staticmethod
    def _prepare_text(text):
        # workaround for a bug in multiline_textsize()
        # when there are empty lines in the text:
        lines = []
        for line in text.split('\n'):
            if line == '':
                line = ' '
            lines.append(line)
        return '\n'.join(lines)

    def _get_font(self, font_size):
        return ImageFont.truetype(self._font_path, font_size)
