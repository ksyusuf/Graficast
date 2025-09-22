from db.models import ApiShare
from datetime import datetime
from services.image_renderer import ImageRenderer
import os

# Mock data for testing
mock_comment = ApiShare(
    comment_id=123,
    comment="""Pamuk şekeri gibi bir hoca. Öğretmez ama öğrenirsiniz, kırıcı konuşma, her yiğidin bir yoğurt yiyişi var dedikleri gibi Süleyman hoca da diğer hocalardan farklı şekilde yoğurt yiyor""",
    comment_date=datetime.now(),
    writer_name="Anonim",
    uni_name="SAKARYA UYGULAMALI BİLİMLER ÜNİVERSİTESİ",
    dep_name="MATEMATİK VE FEN BİLİMLERİ EĞİTİMİ BÖLÜMÜ",
    ins_name="SÜLEYMAN A.",
    image_template_type="instagram-post-square"
)

# Create test_render directory if it doesn't exist
test_render_dir = os.path.join(os.path.dirname(__file__), "test_render")
os.makedirs(test_render_dir, exist_ok=True)

# Instantiate the renderer with correct font path
font_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "OpenSans-VariableFont_wdth,wght.ttf")
renderer = ImageRenderer(font_path)

# Render the image
image = renderer.render(mock_comment)

# Save the image
image_path = os.path.join(test_render_dir, f"test_image_{mock_comment.comment_id}.png")
image.save(image_path)

print(f"Image saved to: {image_path}")