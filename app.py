from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = Flask(__name__)
# Gizli anahtar: Oturum güvenliği ve sepetin hafızada tutulması için şarttır.
app.secret_key = 'Voxor_B2B_Sifre_99!*Oto_Volkan' 

# --- GMAIL AYARLARI ---
# Burayı kendi bilgilerine göre doldurmayı unutma ustam!
GMAIL_ADRESIM = "senin_epostan@gmail.com" 
GMAIL_SIFREM = "xxxx xxxx xxxx xxxx" # Google'dan aldığın 16 haneli uygulama şifresi

# --- EXCEL VERİSİ YÜKLEME ---
def verileri_getir():
    try:
        # Excel'deki ürün ve resim bilgilerini okur
        df = pd.read_excel('urunler.xlsx')
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Excel okuma hatası: {e}")
        return []

# --- E-POSTA GÖNDERME FONKSİYONU ---
def siparis_maili_gonder(bayi_adi, sepet_detay):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_ADRESIM
        msg['To'] = GMAIL_ADRESIM # Siparişler senin mailine gelir
        msg['Subject'] = f"YENİ B2B SİPARİŞİ: {bayi_adi}"

        icerik = f"Sayın Yönetici,\n\n{bayi_adi} bayisinden yeni bir sipariş geldi.\n\nSİPARİŞ İÇERİĞİ:\n{sepet_detay}\n\nLütfen en kısa sürede işleme alınız."
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

# --- SAYFA YÖNLENDİRMELERİ ---
@app.route('/')
def home():
    if 'bayi' in session:
        urunler = verileri_getir()
        # Excel'den gelen resim isimlerini otomatik BÜYÜK HARFE çeviriyoruz ki hata çıkmasın
        for urun in urunler:
            if 'resim' in urun:
                urun['resim'] = str(urun['resim']).upper()
        return render_template('index.html', urunler=urunler, bayi=session['bayi'])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        bayi_kodu = request.form.get('bayi_kodu')
        if bayi_kodu:
            session['bayi'] = bayi_kodu
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/siparis_tamamla', methods=['POST'])
def siparis_tamamla():
    if 'bayi' not in session:
        return jsonify({"durum": "hata", "mesaj": "Oturum açık değil"}), 401
    
    veriler = request.json
    sepet = veriler.get('sepet', '')
    bayi = session['bayi']
    
    # Siparişi e-posta ile yöneticiye gönderir
    if siparis_maili_gonder(bayi, sepet):
        return jsonify({"durum": "basarili", "mesaj": "Siparişiniz merkeze iletildi!"})
    else:
        return jsonify({"durum": "hata", "mesaj": "Sipariş e-posta ile gönderilemedi."})

@app.route('/logout')
def logout():
    session.pop('bayi', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)