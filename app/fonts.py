import subprocess
import sys
from collections import defaultdict


class Fonts:
    def __init__(self):
        self.fonts = defaultdict(dict)

    def parse_fonts(self, raw):
        """ adds the found fonts the the fonts list
        :param raw: command to be run to get the raw font list from the system
        :return: true if fonts were added false if not
        """

        if raw.returncode != 0:
            return {'error': 'an error occurred while processing the fonts'}

        for line in raw.stdout.decode('utf-8').split('\n'):
            font = line.split(':')
            if len(font) < 3:
                continue
            # ignore non true type fonts
            if '.ttf' in font[0] or '.otf' in font[0]:
                fontname = font[1].replace('\\', '')
                fontpath = font[0].strip()
                fontstyle = font[2][6:].strip().split(',')[0]

                if ',' in fontname:
                    fontname = fontname.split()[0]
                fontname = fontname.strip()

                self.fonts[fontname][fontstyle] = fontpath
            else:
                pass

    def scan_global_fonts(self):
        """ Populate the font list from the system.

        On Linux/macOS this uses fontconfig (``fc-list``). On Windows, where
        fontconfig is normally absent, it enumerates the system and per-user
        font folders directly and reads each font's family/style with Pillow.
        """
        if sys.platform == 'win32':
            self.scan_windows_fonts()
            return

        command = ['fc-list']
        try:
            raw = subprocess.run(command, stdout=subprocess.PIPE)
        except FileNotFoundError:
            print('fc-list not found', file=sys.stderr)
            sys.exit(2)

        self.parse_fonts(raw)

    def scan_windows_fonts(self):
        """ Enumerate TrueType/OpenType fonts from the Windows font folders and
        read their family/style names via Pillow (no fontconfig dependency). """
        import os
        import glob
        from PIL import ImageFont

        folders = [os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')]
        local_appdata = os.environ.get('LOCALAPPDATA')
        if local_appdata:
            folders.append(os.path.join(
                local_appdata, 'Microsoft', 'Windows', 'Fonts'))

        for folder in folders:
            for pattern in ('*.ttf', '*.otf', '*.ttc'):
                for path in glob.glob(os.path.join(folder, pattern)):
                    try:
                        family, style = ImageFont.truetype(path).getname()
                    except Exception:
                        continue
                    if family:
                        self.fonts[family][style or 'Regular'] = path

    def scan_fonts_folder(self, folder):
        """ Get a list of all fonts that are available to the user who runs this
        :return: raw output of the command fc-list
        """
        cmd = ['fc-scan', '--format',
               '%{file}:%{family}:style=%{style}\n', folder]
        try:
            raw = subprocess.run(cmd, stdout=subprocess.PIPE)
        except FileNotFoundError:
            print('fc-list not found', file=sys.stderr)
            sys.exit(2)

        self.parse_fonts(raw)

    def fontlist(self):
        return sorted(self.fonts, key=str.lower)

    def fonts_available(self):
        if len(self.fonts) == 0:
            return False
        else:
            return len(self.fonts)
