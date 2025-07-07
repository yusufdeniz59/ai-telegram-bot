import requests
import json
from datetime import datetime
import os
from configparser import ConfigParser
import re
from bs4 import BeautifulSoup
from googlesearch import search
import openai

# Load API keys from config
config = ConfigParser()
config.read('config/settings.ini')

# Get OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    OPENAI_API_KEY = config.get('OpenAI', 'api_key', fallback=None)

if OPENAI_API_KEY:
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

def should_use_web(message: str) -> bool:
    """Check if the message should trigger web search"""
    # Güncel olaylar, haberler, savaş, ekonomi vb. ile ilgili anahtar kelimeler
    keywords = [
        "savaş", "son durum", "bugün", "dün", "gündem", "enflasyon", "deprem", 
        "güncel", "zam", "seçim", "kur", "dolar", "euro", "altın", "borsa",
        "iran", "israil", "ukrayna", "rusya", "abd", "çin", "türkiye",
        "haber", "gelişme", "olay", "kriz", "anlaşma", "toplantı", "zirve",
        "2024", "2023", "bu ay", "bu hafta", "son dakika", "acil", "önemli"
    ]
    return any(word in message.lower() for word in keywords)

def clean_text(text: str) -> str:
    """Clean and extract meaningful text from HTML content"""
    if not text:
        return ""
    
    # HTML etiketlerini temizle
    soup = BeautifulSoup(text, 'html.parser')
    
    # Script ve style etiketlerini kaldır
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Metni al
    text = soup.get_text()
    
    # Fazla boşlukları temizle
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    # Çok uzun metni kısalt (OpenAI token limiti için)
    if len(text) > 3000:
        text = text[:3000] + "..."
    
    return text

def search_google(query: str, num_results: int = 3) -> list:
    """Search Google and return results"""
    try:
        results = []
        search_query = f"{query} güncel haber son durum"
        
        for url in search(search_query, num_results=num_results, lang="tr"):
            try:
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()
                
                content = clean_text(response.text)
                if content and len(content) > 100:  # Anlamlı içerik varsa
                    results.append({
                        'url': url,
                        'content': content[:1000]  # İlk 1000 karakter
                    })
            except Exception as e:
                continue
        
        return results
    except Exception as e:
        print(f"Google search error: {e}")
        return []

def summarize_with_gpt(content_list: list, query: str) -> str:
    """Summarize search results using GPT"""
    try:
        if not OPENAI_API_KEY or not content_list:
            return "📡 Güncel bilgi alınamadı. Lütfen daha sonra tekrar deneyin."
        
        # İçerikleri birleştir
        combined_content = "\n\n".join([f"Kaynak: {item['url']}\nİçerik: {item['content']}" for item in content_list])
        
        prompt = f"""
        Aşağıdaki web içeriklerini analiz ederek "{query}" konusu hakkında güncel ve özet bilgi ver.
        
        Kurallar:
        1. Sadece güncel ve doğrulanabilir bilgileri kullan
        2. Türkçe olarak yanıtla
        3. Kısa ve öz tut (maksimum 300 kelime)
        4. Kaynakları belirt
        5. Eğer güncel bilgi yoksa bunu belirt
        
        Web İçerikleri:
        {combined_content}
        
        Özet:
        """
        
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sen güncel haber ve olayları analiz eden bir asistan. Sadece verilen kaynaklardaki bilgileri kullan."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return f"📡 Özetleme hatası: {str(e)}"

def get_web_summary(query: str) -> str:
    """Get web summary for a query"""
    try:
        print(f"🔍 Web araması yapılıyor: {query}")
        
        # Google'da ara
        search_results = search_google(query)
        
        if not search_results:
            return "📡 Bu konuyla ilgili güncel bilgi bulunamadı."
        
        # GPT ile özetle
        summary = summarize_with_gpt(search_results, query)
        
        return f"📡 **{query}** - Güncel Bilgi:\n\n{summary}"
        
    except Exception as e:
        return f"📡 Web arama hatası: {str(e)}"

def get_weather(city="Istanbul"):
    """Get current weather for a city"""
    try:
        # You can add your weather API key to config/settings.ini
        # weather_api_key = config.get('Weather', 'api_key', fallback=None)
        
        # For now, return a mock response
        weather_data = {
            "city": city,
            "temperature": "22°C",
            "condition": "Güneşli",
            "humidity": "65%",
            "wind": "15 km/h"
        }
        
        return f"🌤️ {city} Hava Durumu:\n🌡️ Sıcaklık: {weather_data['temperature']}\n☀️ Durum: {weather_data['condition']}\n💧 Nem: {weather_data['humidity']}\n💨 Rüzgar: {weather_data['wind']}"
    except Exception as e:
        return f"Hava durumu bilgisi alınamadı: {str(e)}"

def get_exchange_rates():
    """Get current exchange rates"""
    try:
        # Mock exchange rates (you can integrate with a real API)
        rates = {
            "USD/TRY": "31.45",
            "EUR/TRY": "34.20",
            "GBP/TRY": "39.80",
            "Gold": "2,150 TL/gr"
        }
        
        result = "💱 Güncel Döviz Kurları:\n"
        for currency, rate in rates.items():
            result += f"💰 {currency}: {rate}\n"
        
        return result
    except Exception as e:
        return f"Döviz kurları alınamadı: {str(e)}"

def get_tr_news():
    """Get latest Turkish news"""
    try:
        # Mock Turkish news (you can integrate with a real news API)
        news = [
            "🇹🇷 Türkiye'de yeni teknoloji yatırımları başlatıldı",
            "📈 Borsa İstanbul'da pozitif seyir",
            "🏭 Sanayi üretimi artış gösterdi",
            "🎓 Eğitim sisteminde yeni düzenlemeler"
        ]
        
        result = "📰 Türkiye Gündemi:\n"
        for i, headline in enumerate(news, 1):
            result += f"{i}. {headline}\n"
        
        return result
    except Exception as e:
        return f"Türkiye haberleri alınamadı: {str(e)}"

def get_world_news():
    """Get latest world news"""
    try:
        # Mock world news (you can integrate with a real news API)
        news = [
            "🌍 Küresel iklim değişikliği zirvesi düzenlendi",
            "💻 Yapay zeka teknolojilerinde yeni gelişmeler",
            "🏥 Sağlık sektöründe inovasyon projeleri",
            "🚀 Uzay araştırmalarında yeni keşifler"
        ]
        
        result = "🌐 Dünya Gündemi:\n"
        for i, headline in enumerate(news, 1):
            result += f"{i}. {headline}\n"
        
        return result
    except Exception as e:
        return f"Dünya haberleri alınamadı: {str(e)}"

def get_daily_briefing():
    """Get comprehensive daily briefing with weather, exchange rates, and news"""
    try:
        today = datetime.now().strftime("%d.%m.%Y %A")
        
        briefing = f"📊 GÜNLÜK BÜLTEN - {today}\n\n"
        
        # Add weather
        briefing += get_weather() + "\n\n"
        
        # Add exchange rates
        briefing += get_exchange_rates() + "\n"
        
        # Add Turkish news
        briefing += get_tr_news() + "\n"
        
        # Add world news
        briefing += get_world_news()
        
        return briefing
    except Exception as e:
        return f"Günlük bülten hazırlanamadı: {str(e)}"

if __name__ == "__main__":
    # Test the functions
    print("Testing web_data_engine functions...")
    print("\n" + "="*50)
    print(get_daily_briefing())
