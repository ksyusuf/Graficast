from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
import os
import requests
from io import BytesIO


class ImageRenderer:
    def __init__(self, text_font_path: str = "assets/fonts/OpenSans-VariableFont_wdth,wght.ttf"):
        if not os.path.exists(text_font_path):
            raise FileNotFoundError(f"Metin font dosyası bulunamadı: {text_font_path}")
        
        self.text_font_path = text_font_path
        self.emoji_cache = {}  # Emoji önbelleği

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
                # Normal metin
                bbox = text_font.getbbox(char)
                draw.text((current_x, y), char, font=text_font, fill=fill)
                current_x += bbox[2]
        
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

    def _draw_headers(self, draw: ImageDraw.Draw, api_share_data, header_font: ImageFont.FreeTypeFont, 
                     text_color: tuple, content_padding_x: int, current_y: int) -> int:
        """Başlıkları çizer ve son y pozisyonunu döndürür"""
        # Üniversite
        title = api_share_data.uni_name
        draw.text((content_padding_x, current_y), title, font=header_font, fill=text_color)
        current_y += header_font.getbbox(title)[3] + 15

        # Bölüm ve Eğitmen
        if api_share_data.dep_name:
            draw.text((content_padding_x, current_y), api_share_data.dep_name, font=header_font, fill=text_color)
            current_y += header_font.getbbox(api_share_data.dep_name)[3] + 15
            
            if api_share_data.ins_name:
                draw.text((content_padding_x, current_y), api_share_data.ins_name, font=header_font, fill=text_color)
                current_y += header_font.getbbox(api_share_data.ins_name)[3] + 40
            else:
                current_y += 30
        else:
            current_y += 30

        return current_y

    def _draw_comment(self, draw: ImageDraw.Draw, comment: str, text_font: ImageFont.FreeTypeFont,
                     text_color: tuple, content_width: int, current_y: int, frame_rect: list,
                     content_padding_x: int) -> int:
        """Yorum metnini çizer ve son y pozisyonunu döndürür"""
        line_height = text_font.getbbox("A")[3] + 20
        wrapped_lines = textwrap.wrap(comment, width=int(content_width / 20))
        
        # Maksimum yüksekliği hesapla
        footer_padding = 10  # footer'dan padding
        footer_text_height = text_font.getbbox("A")[3]  # footer metin yüksekliği
        max_comment_height = frame_rect[3] - current_y - (footer_padding + footer_text_height + 10)  # 10px ekstra boşluk
        
        available_lines = int(max_comment_height / line_height)
        
        if len(wrapped_lines) > available_lines:
            wrapped_lines = wrapped_lines[:available_lines]
            last_line = wrapped_lines[-1]
            while len(last_line) > 3 and text_font.getbbox(last_line + "...")[2] > content_width:
                last_line = last_line[:-1]
            wrapped_lines[-1] = last_line + "..."

        text_y = current_y + 5
        text_x = content_padding_x

        for line in wrapped_lines:
            text_y = self._draw_text_with_emojis(
                draw, line, (text_x, text_y),
                text_font, text_color, 40
            )[1] + 18  # satır aralığı

        return text_y

    def _draw_footer(self, draw: ImageDraw.Draw, api_share_data, footer_font: ImageFont.FreeTypeFont,
                    frame_rect: list, content_padding_x: int, width: int) -> None:
        """Alt bilgiyi çizer"""
        bottom_padding = 50
        date_str = api_share_data.comment_date.strftime("%d.%m.%Y %H:%M:%S")
        writer = api_share_data.writer_name or "Anonim"
        footer = f"{date_str} - {writer}"
        footer_bbox = footer_font.getbbox(footer)
        footer_x = width - content_padding_x - footer_bbox[2]  # Sağdan padding kadar içeride
        footer_y = frame_rect[3] - bottom_padding - footer_bbox[3]  # Alttan padding kadar yukarıda
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
        header_font = ImageFont.truetype(self.text_font_path, 40)
        header_font.set_variation_by_axes([700])
        text_font = ImageFont.truetype(self.text_font_path, 40)
        footer_font = ImageFont.truetype(self.text_font_path, 38)

        # İçerik için padding değerlerini hesapla
        content_padding_x = frame_rect[0] + 50
        content_padding_y = frame_rect[1] + 40
        current_y = content_padding_y
        content_width = frame_rect[2] - frame_rect[0] - 100

        # Başlıkları çiz
        current_y = self._draw_headers(draw, api_share_data, header_font, text_color, content_padding_x, current_y)

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
        current_y = self._draw_comment(draw, api_share_data.comment, text_font, text_color, 
                                     content_width, current_y, frame_rect, content_padding_x)

        # Alt bilgiyi çiz
        self._draw_footer(draw, api_share_data, footer_font, frame_rect, content_padding_x, width)
        return image
