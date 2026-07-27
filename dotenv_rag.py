import os

def load_dotenv(dotenv_path=".env"):
    """
    Belirtilen .env dosyasındaki çevre değişkenlerini okur 
     ve os.environ içerisine yükler.
    """
    # Dosyanın var olup olmadığını kontrol et
    if not os.path.exists(dotenv_path):
        # Dosya yoksa sessizce geç (veya istersen uyarı yazdırabilirsin)
        return False

    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            # Satırın başındaki ve sonundaki boşlukları temizle
            line = line.strip()
            
            # Boş satırları veya yorum satırlarını (#) atla
            if not line or line.startswith("#"):
                continue
            
            # Sadece ilk '=' işaretine göre böl (değerin içinde de = olabilir)
            if "=" in line:
                key, value = line.split("=", 1)
                
                # Key ve value etrafındaki boşlukları temizle
                key = key.strip()
                value = value.strip()
                
                # Eğer değer tırnak işaretleri (" veya ') içindeyse bunları kaldır
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                # Çevre değişkeni olarak sisteme kaydet
                os.environ[key] = value
                
    return True