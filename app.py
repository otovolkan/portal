from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = Flask(__name__)
# Oturum güvenliği için anahtar (sepetteki ürünleri ve girişi hatırlar)
app.secret_key = 'otovolkan_gizli_anahtar_2026'

# --- GMAIL AYARLARI ---
# Burayı kendi bilgilerine göre doldur ustam!
GMAIL_ADRESIM = "voxoraku@gmail.com" 
GMAIL_SIFREM = "gpml fttc uzzu zvaa" # Google'dan aldığın 16 haneli uygulama şifresi

def verileri_hazirla():
    try:
        if not os.path.exists('urunler.xlsx'):
            print("HATA: urunler.xlsx bulunamadı!")
            return [], []
        
        # Excel'i oku (openpyxl kütüphanesini kullanır)
        df = pd.read_excel('urunler.xlsx', engine='openpyxl')
        df = df.fillna('')
        
        # Sütun isimlerini standart hale getiriyoruz (boşlukları sil, küçük harf yap)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Excel'deki başlıkları kodla eşleştiriyoruz (Ürün Adı -> urun_adi gibi)
        mapping = {
            'ürün adı': 'urun_adi', 'urun adi': 'urun_adi', 'adi': 'urun_adi', 'ad': 'urun_adi',
            'marka': 'marka', 'brand': 'marka',
            'fiyat': 'fiyat', 'price': 'fiyat', 'tutar': 'fiyat',
            'resim': 'resim', 'görsel': 'resim', 'image': 'resim'
        }
        df = df.rename(columns=mapping)
        
        urunler = df.to_dict(orient='records')
        
        for u in urunler:
            # RESİM DÜZELTME: İsimleri büyük harfe çevir (KAMPANYA1.PNG için)
            resim_adi = str(u.get('resim', 'YOK.PNG')).strip().upper()
            u['resim'] = resim_adi
            
        markalar = sorted(list(set([str(u.get('marka', '')) for u in urunler if u.get('marka')])))
        return urunler, markalar
    except Exception as e:
        print(f"Excel Okuma Hatası: {e}")
        return [], []

def siparis_maili_gonder(bayi_adi, sepet_detay):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_ADRESIM
        msg['To'] = GMAIL_ADRESIM # Siparişler sana gelsin
        msg['Subject'] = f"YENİ B2B SİPARİŞİ: {bayi_adi}"

        icerik = f"Sayın Yönetici,\n\n{bayi_adi} bayisinden yeni sipariş geldi.\n\nSİPARİŞ İÇERİĞİ:\n{sepet_detay}\n\nLütfen en kısa sürede işleme alınız."
        msg.attach(MIMEText(icerik, 'plain', 'utf-8'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_ADRESIM, GMAIL_SIFREM)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Mail gönderme hatası: {e}")
        return False

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
    if 'bayi' not in session:
        return jsonify({"durum": "hata", "message": "Oturum kapalı"}), 401
    
    veriler = request.json
    sepet = veriler.get('sepet', '')
    
    if siparis_maili_gonder(session['bayi'], sepet):
        return jsonify({"durum": "basarili"})
    else:
        return jsonify({"durum": "hata", "message": "Mail gönderilemedi."})

@app.route('/cikis')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)