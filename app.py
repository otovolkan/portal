from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = Flask(__name__)
app.secret_key = 'Oto959595-'

# --- GMAIL AYARLARI ---
GMAIL_ADRESIM = "voxoraku@gmail.com" 
GMAIL_SIFREM = "gpml fttc uzzu zvaa" # Google'dan aldığın 16 haneli uygulama şifresi

def verileri_hazirla():
    try:
        if not os.path.exists('urunler.xlsx'):
            return [], []
        
        df = pd.read_excel('urunler.xlsx')
        df = df.fillna('') # Boş yerleri doldur
        
        # Sütun isimlerini standart hale getiriyoruz (Boşlukları sil, küçük harf yap)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Eğer sütun isimlerin Excel'de farklıysa bunları düzeltiyoruz
        column_mapping = {
            'ürün adı': 'urun_adi',
            'urun adi': 'urun_adi',
            'fiyat': 'fiyat',
            'marka': 'marka',
            'resim': 'resim'
        }
        df = df.rename(columns=column_mapping)
        
        urunler = df.to_dict(orient='records')
        
        # Resim isimlerini BÜYÜK harf yap (KAMPANYA1.PNG için)
        for u in urunler:
            u['resim'] = str(u.get('resim', 'YOK.PNG')).strip().upper()
            
        markalar = sorted(list(set([str(u.get('marka', '')) for u in urunler if u.get('marka')])))
        return urunler, markalar
    except Exception as e:
        print(f"Hata: {e}")
        return [], []

@app.route('/')
def home():
    if 'bayi' not in session:
        return redirect(url_for('login'))
    
    urunler, markalar = verileri_hazirla()
    return render_template('index.html', urunler=urunler, markalar=markalar, bayi=session['bayi'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        kod = request.form.get('bayi_kodu')
        if kod:
            session['bayi'] = kod
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/siparis_tamamla', methods=['POST'])
def siparis_tamamla():
    if 'bayi' not in session: return jsonify({"durum": "hata"}), 401
    
    # Sipariş maili gönderme kısmı (İsteğe bağlı, istersen aktif et)
    return jsonify({"durum": "basarili"})

@app.route('/cikis')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)