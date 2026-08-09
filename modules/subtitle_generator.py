import os
from PIL import Image, ImageDraw, ImageFont

# Pillow 10+ sürüm uyumluluk yaması
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

# Fontu repodan, sisteme bağımlı olmadan yükle.
# assets/fonts/Font.ttf dosyasını repoya eklemen gerekiyor (bkz. açıklama).
_FONT_PATH_BUNDLED = os.path.join(os.getcwd(), "assets", "fonts", "Font.ttf")

_FALLBACK_SYSTEM_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]

_FONT_CACHE = {}


def _load_font(size=75):
    """
    Fontu önce repoya gömülü dosyadan, bulunamazsa sistem fontlarından
    yükler. Hiçbiri bulunamazsa açıkça uyarı basar (sessizce PIL'in
    ~10px'lik görünmez varsayılan fontuna düşmez).
    """
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]

    candidates = [_FONT_PATH_BUNDLED] + _FALLBACK_SYSTEM_FONTS

    for path in candidates:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size=size)
                _FONT_CACHE[size] = font
                return font
            except Exception:
                continue

    print(
        "   🚨 UYARI: Hiçbir .ttf font dosyası bulunamadı! "
        "Altyazılar PIL'in minik varsayılan fontuyla (neredeyse görünmez) "
        "çizilecek. assets/fonts/Font.ttf ekleyerek bunu çöz."
    )
    font = ImageFont.load_default()
    _FONT_CACHE[size] = font
    return font


class MoviePySubtitleGenerator:
    @staticmethod
    def create_text_clip_image(words_group, active_word_index, img_size=(1080, 1920)):
        img = Image.new("RGBA", img_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Gövdeyi daha tok tutmak için boyutu 75 yapıyoruz
        font = _load_font(size=75)

        # --- SATIRLARA BÖLME MANTIĞI ---
        max_width = img_size[0] - 140  # Sağdan soldan güvenlik payı
        lines = []
        current_line = []
        current_line_width = 0

        for i, w in enumerate(words_group):
            word_str = w['word'].upper() + " "
            try:
                bbox = draw.textbbox((0, 0), word_str, font=font)
                word_w = bbox[2] - bbox[0]
            except Exception:
                word_w = 150

            if current_line_width + word_w > max_width and current_line:
                lines.append(current_line)
                current_line = []
                current_line_width = 0

            current_line.append({'index': i, 'text': word_str, 'width': word_w})
            current_line_width += word_w

        if current_line:
            lines.append(current_line)

        # --- DİKEY TAM ORTALAMA (Y Ekseni) ---
        line_height = 95
        total_text_height = len(lines) * line_height
        # Ekran yüksekliğinin yarısından (1920 / 2 = 960) toplam metin yüksekliğinin yarısını çıkararak dikeyde tam ortalıyoruz
        current_y = (img_size[1] / 2) - (total_text_height / 2)

        # --- ÇİZİM VE YATAY ORTALAMA (X Ekseni) + ET KOYU KONTUR ---
        for line in lines:
            line_total_width = sum([item['width'] for item in line])
            # Her satırı kendi genişliğine göre yatayda ekrana ortala
            current_x = (img_size[0] - line_total_width) / 2

            for item in line:
                is_active = (item['index'] == active_word_index)
                color = "#00FFFF" if is_active else "#FFFFFF"

                # stroke_width=10 ile ince fontları bile Extra Bold gösteren siyah zırh
                draw.text(
                    (current_x, current_y), 
                    item['text'], 
                    font=font, 
                    fill=color, 
                    stroke_width=10, 
                    stroke_fill="#000000"
                )
                current_x += item['width']

            current_y += line_height

        return img
