import os
import pandas as pd
from flask import Flask

app = Flask(__name__)

@app.route('/')
def test():
    dosyalar = os.listdir('.') # Klasördeki her şeyi listeler
    if 'urunler.xlsx' in dosyalar:
        try:
            df = pd.read_excel('urunler.xlsx')
            return f"Excel bulundu ve okundu! Toplam {len(df)} ürün var."
        except Exception as e:
            return f"Excel bulundu ama okuma hatası: {e}"
    else:
        return f"HATA: urunler.xlsx dosyası sunucuda bulunamadı! Mevcut dosyalar: {dosyalar}"

if __name__ == '__main__':
    app.run(debug=True)