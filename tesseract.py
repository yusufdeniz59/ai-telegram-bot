from PIL import Image
import pytesseract
import os

# Eğer Windows kullanıyorsan Tesseract yolu belirt
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Burayı kendi kurulum yoluna göre değiştir

def ocr_image_to_text(image_path, lang='eng'):
    try:
        text = pytesseract.image_to_string(Image.open(image_path), lang=lang)  # Varsayılan İngilizce
        return text.strip()
    except Exception as e:
        return f"Hata: {e}"

# Örnek kullanım - Windows dosya yolu düzeltmesi
image_file = r"C:\Users\Yusuf\OneDrive\Desktop\ai projects\DigiMe\photos\1.jpg"  # Raw string kullanarak
# Alternatif: image_file = "C:/Users/Yusuf/OneDrive/Desktop/ai projects/DigiMe/photos/1.jpg"  # Forward slash kullanarak

text_result = ocr_image_to_text(image_file, lang='eng')  # İngilizce ile test
print(text_result)
