from collections.abc import Callable
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import re
import requests
from io import BytesIO


class ImageRenderer:
    def __init__(self, text_font_path: str = "assets/fonts/OpenSans-VariableFont_wdth,wght.ttf"):
        if not os.path.exists(text_font_path):
            raise FileNotFoundError(f"Metin font dosyası bulunamadı: {text_font_path}")
        
        self.text_font_path = text_font_path
        self.emoji_cache = {}  # Emoji önbelleği

    def _text_width(self, font: ImageFont.FreeTypeFont, text: str) -> float:
        if hasattr(font, "getlength"):
            return float(font.getlength(text))
        bbox = font.getbbox(text)
        return float(bbox[2] - bbox[0])

    def _text_line_height(self, font: ImageFont.FreeTypeFont, sample: str = "AyİğÇg") -> int:
        bbox = font.getbbox(sample)
        return max(1, bbox[3] - bbox[1])

    def _mixed_line_width(self, font: ImageFont.FreeTypeFont, line: str, emoji_size: int) -> float:
        w = 0.0
        for ch in line:
            if self._is_emoji(ch):
                w += float(emoji_size)
            else:
                w += self._text_width(font, ch)
        return w

    def _break_word_to_width(
        self, font: ImageFont.FreeTypeFont, word: str, max_width: float, emoji_size: int | None = None
    ) -> list[str]:
        measure = (
            (lambda t: self._mixed_line_width(font, t, emoji_size)) if emoji_size is not None else (lambda t: self._text_width(font, t))
        )
        if measure(word) <= max_width:
            return [word]
        parts: list[str] = []
        current = ""
        for ch in word:
            trial = current + ch
            if measure(trial) <= max_width:
                current = trial
            else:
                if current:
                    parts.append(current)
                current = ch
                if measure(current) > max_width:
                    parts.append(current)
                    current = ""
        if current:
            parts.append(current)
        return parts if parts else [word[:1]]

    def _wrap_to_pixel_width(
        self,
        font: ImageFont.FreeTypeFont,
        text: str,
        max_width: float,
        emoji_size: int | None = None,
    ) -> list[str]:
        text = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
        if not text:
            return []
        measure_line = (
            (lambda s: self._mixed_line_width(font, s, emoji_size)) if emoji_size is not None else (lambda s: self._text_width(font, s))
        )

        lines: list[str] = []
        current_words: list[str] = []

        def flush_words() -> None:
            nonlocal current_words
            if current_words:
                lines.append(" ".join(current_words))
                current_words = []

        for word in text.split(" "):
            if not word:
                continue
            trial = (" ".join(current_words) + " " + word).strip() if current_words else word
            if measure_line(trial) <= max_width:
                current_words.append(word)
                continue
            flush_words()
            broken = self._break_word_to_width(font, word, max_width, emoji_size)
            for j, piece in enumerate(broken):
                if j < len(broken) - 1:
                    lines.append(piece)
                else:
                    current_words = [piece] if piece else []
        flush_words()
        return lines

    def _strip_suffix_ci(self, s: str, suffix: str) -> str | None:
        if len(s) < len(suffix):
            return None
        if s.upper().endswith(suffix.upper()):
            return s[: len(s) - len(suffix)].rstrip()
        return None

    def _abbreviate_uni_name(self, s: str) -> str:
        if not s:
            return s
        s = s.strip()
        core = self._strip_suffix_ci(s, "ÜNİVERSİTESİ")
        if core is not None:
            return f"{core} Ü.".strip()
        return s

    def _abbreviate_dep_name(self, s: str) -> str:
        if not s:
            return s
        s = s.strip()
        core = self._strip_suffix_ci(s, "BÖLÜMÜ")
        if core is not None:
            return f"{core} B.".strip()
        return s

    def _truncate_line_visual(self, font: ImageFont.FreeTypeFont, text: str, max_width: float, suffix: str = "…") -> str:
        if self._text_width(font, text) <= max_width:
            return text
        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            candidate = text[:mid].rstrip() + suffix
            if self._text_width(font, candidate) <= max_width:
                low = mid
            else:
                high = mid - 1
        return (text[:low].rstrip() + suffix) if low > 0 else suffix

    def _is_emoji(self, char: str) -> bool:
        """Karakterin emoji olup olmadığını kontrol eder"""
        return len(char.encode('utf-8')) > 2

    def _get_emoji_image(self, emoji: str, size: int = 38) -> Image.Image:
        """Emoji görselini CDN'den alır veya önbellekten döndürür"""
        # Emoji için benzersiz bir anahtar oluştur
        cache_key = f"{emoji}_{size}"
        
        # Önbellekte varsa döndür
        if cache_key in self.emoji_cache:
            return self.emoji_cache[cache_key]
        
        try:
            # Emoji kodunu hex'e çevir ve formatla
            emoji_hex = '-'.join([f"{ord(c):x}" for c in emoji])
            # Twemoji CDN URL'i
            url = f"https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/{emoji_hex}.png"
            
            response = requests.get(url)
            if response.status_code == 200:
                # Görseli yükle ve boyutlandır
                emoji_img = Image.open(BytesIO(response.content))
                # RGBA moduna çevir
                emoji_img = emoji_img.convert('RGBA')
                emoji_img = emoji_img.resize((size, size), Image.Resampling.LANCZOS)
                
                # Önbelleğe kaydet
                self.emoji_cache[cache_key] = emoji_img
                return emoji_img
            else:
                print(f"Emoji indirilemedi: {emoji} (URL: {url}, Status: {response.status_code})")
                return Image.new("RGBA", (size, size), (0, 0, 0, 0))
        except Exception as e:
            print(f"Emoji işleme hatası: {e} (Emoji: {emoji})")
            return Image.new("RGBA", (size, size), (0, 0, 0, 0))

    def _draw_text_with_emojis(self, draw: ImageDraw.Draw, text: str, position: tuple, 
                             text_font: ImageFont.FreeTypeFont, fill: tuple, 
                             emoji_size: int = 40) -> tuple:
        """Metni ve emojileri birlikte çizer"""
        x, y = position
        current_x = x
        line_height = text_font.getbbox("A")[3]
        
        # Metin yüksekliğini hesapla
        text_height = text_font.getbbox("A")[3]
        # Emoji için dikey offset hesapla (metin yüksekliğinin ortasına hizala + ekstra offset)
        emoji_offset = ((text_height - emoji_size) // 2) + 8  # 8 piksel daha aşağı
        
        for char in text:
            if self._is_emoji(char):
                # Emoji görselini al
                emoji_img = self._get_emoji_image(char, emoji_size)
                # Emojiyi yerleştir (dikey offset ile)
                draw._image.paste(emoji_img, (int(current_x), int(y + emoji_offset)), emoji_img.split()[3])
                current_x += emoji_size
            else:
                # Normal metin (tam genişlik: sol taşıma + sağ ilerleme)
                bbox = text_font.getbbox(char)
                draw.text((current_x, y), char, font=text_font, fill=fill)
                current_x += bbox[2] - bbox[0]
        
        return (current_x, y + line_height)

    def _create_gradient_background(self, width: int, height: int, colors: list) -> Image.Image:    
        """Gradyan arka plan oluşturur
        https://colorkit.co/gradient-maker/c8ff9e-ffc2ef-aefaf6/
        """
        image = Image.new("RGBA", (width, height), colors[-1])
        draw = ImageDraw.Draw(image)
        max_distance = width + height

        for y in range(height):
            for x in range(width):
                distance = (x + y)
                section_size = max_distance / (len(colors) - 1)
                section = int(distance / section_size)
                section_ratio = (distance % section_size) / section_size
                
                color1_index = min(section, len(colors) - 2)
                color2_index = color1_index + 1
                
                r = int(colors[color1_index][0] * (1 - section_ratio) + colors[color2_index][0] * section_ratio)
                g = int(colors[color1_index][1] * (1 - section_ratio) + colors[color2_index][1] * section_ratio)
                b = int(colors[color1_index][2] * (1 - section_ratio) + colors[color2_index][2] * section_ratio)
                
                draw.point((x, y), fill=(r, g, b))
        
        return image

    def _create_frame_with_shadows(self, image: Image.Image, frame_rect: list, frame_radius: int) -> Image.Image:
        """Çerçeve ve gölgeleri oluşturur"""
        width, height = image.size
        
        # Yeni bir beyaz katman oluştur
        frame_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        frame_draw = ImageDraw.Draw(frame_layer)
        
        # Çerçeveyi çiz
        body_color = (255, 255, 255, 255)  # Tam opak beyaz
        frame_draw.rounded_rectangle(frame_rect, radius=frame_radius, fill=body_color)
        
        # Gölgeleri çiz
        shadow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        
        # Ana gölge
        shadow_offset = 15
        shadow_blur = 25
        shadow_color = (0, 0, 0, 40)
        shadow_rect = [
            frame_rect[0] + shadow_offset,
            frame_rect[1] + shadow_offset,
            frame_rect[2] + shadow_offset,
            frame_rect[3] + shadow_offset
        ]
        shadow_draw.rounded_rectangle(shadow_rect, radius=frame_radius, fill=shadow_color)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(shadow_blur))
        
        # İkinci katman gölge
        shadow2_offset = 20
        shadow2_blur = 30
        shadow2_color = (0, 0, 0, 20)
        shadow2_rect = [
            frame_rect[0] + shadow2_offset,
            frame_rect[1] + shadow2_offset,
            frame_rect[2] + shadow2_offset,
            frame_rect[3] + shadow2_offset
        ]
        shadow_draw.rounded_rectangle(shadow2_rect, radius=frame_radius, fill=shadow2_color)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(shadow2_blur))
        
        # Katmanları birleştir: önce gölgeler, sonra çerçeve
        image = Image.alpha_composite(image, shadow_layer)
        image = Image.alpha_composite(image, frame_layer)
        
        # İnce beyaz anahat
        draw = ImageDraw.Draw(image)
        outline_width = 1
        outline_color = (255, 255, 255, 180)
        draw.rounded_rectangle(frame_rect, radius=frame_radius, outline=outline_color, width=outline_width)
        
        return image

    def _draw_wrapped_plain_block(
        self,
        draw: ImageDraw.Draw,
        font: ImageFont.FreeTypeFont,
        axes: list[int],
        text: str,
        text_color: tuple,
        content_padding_x: int,
        content_width: float,
        current_y: int,
        max_y_abs: int,
        line_gap: int,
        block_bottom_pad: int,
    ) -> int:
        """Düz metin bloğunu piksel genişliğine göre sarar; max_y_abs aşılırsa son satırı kısaltır."""
        if not text:
            return current_y
        font.set_variation_by_axes(axes)
        lines = self._wrap_to_pixel_width(font, text, content_width)
        lh = self._text_line_height(font)
        for i, line in enumerate(lines):
            if current_y + lh > max_y_abs:
                line = self._truncate_line_visual(font, line, content_width, "…")
                draw.text((content_padding_x, current_y), line, font=font, fill=text_color)
                return current_y + lh + block_bottom_pad
            draw.text((content_padding_x, current_y), line, font=font, fill=text_color)
            current_y += lh + (line_gap if i < len(lines) - 1 else 0)
        return current_y + block_bottom_pad

    def _uni_dep_header_lines(
        self,
        font: ImageFont.FreeTypeFont,
        text: str,
        content_width: float,
        axes: list[int],
        max_lines: int,
        abbrev_fn: Callable[[str], str],
    ) -> list[str]:
        """Üniversite veya bölüm metnini en fazla max_lines satıra indirir: önce tam metin, taşarsa Ü./B. kısaltma, sonra ..."""
        if not (text or "").strip():
            return []
        font.set_variation_by_axes(axes)
        t = text.strip()
        lines = self._wrap_to_pixel_width(font, t, content_width)
        if len(lines) <= max_lines:
            return lines
        t_abbrev = abbrev_fn(t)
        if t_abbrev != t:
            lines = self._wrap_to_pixel_width(font, t_abbrev, content_width)
        if len(lines) <= max_lines:
            return lines
        merged_tail = " ".join(lines[max_lines - 1 :]).strip()
        head = lines[: max_lines - 1]
        tail = self._truncate_line_visual(font, merged_tail, content_width, "...")
        return head + [tail]

    def _draw_wrapped_plain_lines(
        self,
        draw: ImageDraw.Draw,
        font: ImageFont.FreeTypeFont,
        axes: list[int],
        lines: list[str],
        text_color: tuple,
        content_padding_x: int,
        content_width: float,
        current_y: int,
        max_y_abs: int,
        line_gap: int,
        block_bottom_pad: int,
        truncate_suffix: str = "...",
    ) -> int:
        if not lines:
            return current_y
        font.set_variation_by_axes(axes)
        lh = self._text_line_height(font)
        for i, line in enumerate(lines):
            if current_y + lh > max_y_abs:
                line = self._truncate_line_visual(font, line, content_width, truncate_suffix)
                draw.text((content_padding_x, current_y), line, font=font, fill=text_color)
                return current_y + lh + block_bottom_pad
            draw.text((content_padding_x, current_y), line, font=font, fill=text_color)
            current_y += lh + (line_gap if i < len(lines) - 1 else 0)
        return current_y + block_bottom_pad

    def _draw_headers(
        self,
        draw: ImageDraw.Draw,
        api_share_data,
        text_color: tuple,
        content_padding_x: int,
        current_y: int,
        content_width: float,
        frame_rect: list,
    ) -> int:
        """Başlıkları çizer; üniversite ve bölüm en fazla 2'şer satır (Ü./B. ve gerekirse ...)."""
        header_font = ImageFont.truetype(self.text_font_path, 40)
        reserved_below = 270
        max_y_abs = frame_rect[3] - reserved_below

        uni_raw = (api_share_data.uni_name or "").strip()
        dep_raw = (api_share_data.dep_name or "").strip()

        if api_share_data.ins_name:
            if uni_raw:
                u_lines = self._uni_dep_header_lines(
                    header_font, uni_raw, content_width, [500], 2, self._abbreviate_uni_name
                )
                current_y = self._draw_wrapped_plain_lines(
                    draw,
                    header_font,
                    [500],
                    u_lines,
                    text_color,
                    content_padding_x,
                    content_width,
                    current_y,
                    max_y_abs,
                    5,
                    0,
                )
                if dep_raw:
                    current_y += 8
            if dep_raw:
                d_lines = self._uni_dep_header_lines(
                    header_font, dep_raw, content_width, [500], 2, self._abbreviate_dep_name
                )
                current_y = self._draw_wrapped_plain_lines(
                    draw,
                    header_font,
                    [500],
                    d_lines,
                    text_color,
                    content_padding_x,
                    content_width,
                    current_y,
                    max_y_abs,
                    5,
                    0,
                )
            if uni_raw or dep_raw:
                current_y += 15
            current_y = self._draw_wrapped_plain_block(
                draw,
                header_font,
                [700],
                api_share_data.ins_name.strip(),
                text_color,
                content_padding_x,
                content_width,
                current_y,
                max_y_abs,
                5,
                40,
            )
        elif api_share_data.dep_name:
            if uni_raw:
                u_lines = self._uni_dep_header_lines(
                    header_font, uni_raw, content_width, [500], 2, self._abbreviate_uni_name
                )
                current_y = self._draw_wrapped_plain_lines(
                    draw,
                    header_font,
                    [500],
                    u_lines,
                    text_color,
                    content_padding_x,
                    content_width,
                    current_y,
                    max_y_abs,
                    5,
                    0,
                )
                current_y += 15
            d_lines = self._uni_dep_header_lines(
                header_font, dep_raw, content_width, [700], 2, self._abbreviate_dep_name
            )
            current_y = self._draw_wrapped_plain_lines(
                draw,
                header_font,
                [700],
                d_lines,
                text_color,
                content_padding_x,
                content_width,
                current_y,
                max_y_abs,
                5,
                40,
            )
        else:
            if uni_raw:
                u_lines = self._uni_dep_header_lines(
                    header_font, uni_raw, content_width, [700], 2, self._abbreviate_uni_name
                )
                current_y = self._draw_wrapped_plain_lines(
                    draw,
                    header_font,
                    [700],
                    u_lines,
                    text_color,
                    content_padding_x,
                    content_width,
                    current_y,
                    max_y_abs,
                    5,
                    40,
                )
        return current_y

    def _draw_comment(
        self,
        draw: ImageDraw.Draw,
        comment: str,
        text_font: ImageFont.FreeTypeFont,
        footer_font: ImageFont.FreeTypeFont,
        text_color: tuple,
        content_width: float,
        current_y: int,
        frame_rect: list,
        content_padding_x: int,
    ) -> int:
        """Yorum metnini çizer ve son y pozisyonunu döndürür"""
        emoji_size = 40
        line_height = self._text_line_height(text_font) + 20 # satır yüksekliğini ifade eder.
        wrapped_lines = self._wrap_to_pixel_width(text_font, comment, content_width, emoji_size=emoji_size)

        footer_padding = 10
        footer_text_height = self._text_line_height(footer_font, "0")
        bottom_reserve = footer_padding + footer_text_height + 55
        # Bir satır yüksekliği kadar ek içerik alanı
        max_comment_height = frame_rect[3] - current_y - bottom_reserve + line_height
        max_comment_height = max(max_comment_height, line_height)

        available_lines = max(1, int(max_comment_height // line_height)) if line_height else 1

        ell = "..."
        if len(wrapped_lines) > available_lines:
            wrapped_lines = wrapped_lines[:available_lines]
            last_line = wrapped_lines[-1]
            while len(last_line) > 0 and self._mixed_line_width(text_font, last_line + ell, emoji_size) > content_width:
                last_line = last_line[:-1]
            wrapped_lines[-1] = (last_line.rstrip() + ell) if last_line else ell

        text_y = current_y + 5
        text_x = content_padding_x

        for line in wrapped_lines:
            text_y = self._draw_text_with_emojis(
                draw, line, (text_x, text_y),
                text_font, text_color, emoji_size
            )[1] + 20 # satır yüksekliğini ifade eden kısımla aynı olmalıdır.

        return text_y

    def _draw_footer(self, draw: ImageDraw.Draw, api_share_data, footer_font: ImageFont.FreeTypeFont,
                    frame_rect: list) -> None:
        """Alt bilgiyi çizer; taşarsa tarih/saat ve yazarı kısaltır."""
        bottom_padding = 50
        inner_right = frame_rect[2] - 50
        inner_left = frame_rect[0] + 50
        max_footer_width = inner_right - inner_left

        writer = api_share_data.writer_name or "Anonim"
        dt_full = api_share_data.comment_date.strftime("%d.%m.%Y %H:%M:%S")
        dt_short = api_share_data.comment_date.strftime("%d.%m.%Y %H:%M")
        dt_day = api_share_data.comment_date.strftime("%d.%m.%Y")

        candidates = [
            f"{dt_full} - {writer}",
            f"{dt_short} - {writer}",
            f"{dt_day} - {writer}",
        ]
        footer = candidates[-1]
        for c in candidates:
            if self._text_width(footer_font, c) <= max_footer_width:
                footer = c
                break
        if self._text_width(footer_font, footer) > max_footer_width:
            core = f"{dt_day} - "
            wpart = writer
            while wpart and self._text_width(footer_font, core + wpart + "…") > max_footer_width:
                wpart = wpart[:-1]
            footer = core + (wpart + "…" if wpart else "")

        l, t, r, b = draw.textbbox((inner_left, 0), footer, font=footer_font)
        tw = r - l
        th = b - t
        footer_x = max(inner_left, inner_right - tw)
        footer_y = frame_rect[3] - bottom_padding - th
        draw.text((footer_x, footer_y), footer, font=footer_font, fill=(120, 120, 120))

    def render(self, api_share_data) -> Image.Image:
        width, height = 1080, 1350
        # daha sonra belli paletler ile arkaplan randomize edilebilir.
        colors = [
            (200, 255, 158),  # #c8ff9e (açık yeşil)
            (255, 194, 239),  # #ffc2ef (açık pembe)
            (174, 250, 246)   # #aefaf6 (açık turkuaz)
        ]
        text_color = (30, 30, 30)

        # Arka plan oluştur
        image = self._create_gradient_background(width, height, colors)

        # Çerçeve boyutlarını hesapla
        frame_padding = 100
        frame_radius = 20
        body_width = width - (2 * frame_padding)
        body_height = body_width
        body_y_offset = (height - body_height) // 2
        
        frame_rect = [
            frame_padding,
            body_y_offset,
            width - frame_padding,
            body_y_offset + body_height
        ]

        # Çerçeve ve gölgeleri oluştur
        image = self._create_frame_with_shadows(image, frame_rect, frame_radius)
        draw = ImageDraw.Draw(image)

        # Fontları yükle
        text_font = ImageFont.truetype(self.text_font_path, 40)
        footer_font = ImageFont.truetype(self.text_font_path, 38)

        # İçerik için padding değerlerini hesapla
        content_padding_x = frame_rect[0] + 50
        content_padding_y = frame_rect[1] + 40
        current_y = content_padding_y
        content_width = frame_rect[2] - frame_rect[0] - 100

        # Başlıkları çiz
        current_y = self._draw_headers(
            draw, api_share_data, text_color, content_padding_x, current_y, content_width, frame_rect
        )

        # Ayırıcı çizgi
        divider_height = 2
        divider_y = current_y
        divider_color = (200, 200, 200)
        draw.line(
            [(frame_rect[0], divider_y), (frame_rect[2], divider_y)],
            fill=divider_color,
            width=divider_height
        )
        current_y += divider_height + 30

        # Yorum metnini çiz
        current_y = self._draw_comment(
            draw,
            api_share_data.comment,
            text_font,
            footer_font,
            text_color,
            content_width,
            current_y,
            frame_rect,
            content_padding_x,
        )

        # Alt bilgiyi çiz
        self._draw_footer(draw, api_share_data, footer_font, frame_rect)
        return image
