from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = Flask(__name__)
# Burayı kendine özel bir şifreyle değiştirmeyi unutma ustam!
app.secret_key = 'Voxor_Oto_Volkan_B2B_2026_Gizli'

# --- GMAIL AYARLARI ---
GMAIL_ADRESIM = "senin_epostan@gmail.com" 
GMAIL_SIFREM = "xxxx xxxx xxxx xxxx" 

def verileri_getir():
    try:
        # Dosya yolunu kontrol ediyoruz
        df = pd.read_excel('urunler.xlsx')
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Excel hatası: {e}")
        return []

def siparis_maili_gonder(bayi_adi, sepet_detay):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_ADRESIM
        msg['To'] = GMAIL_ADRESIM
        msg['Subject'] = f"YENİ B2B SİPARİŞİ: {bayi_adi}"
        icerik = f"Sayın Yönetici,\n\n{bayi_adi} bayisinden yeni sipariş geldi.\n\nİÇERİĞİ:\n{sepet_detay}"
        msg.attach(MIMEText(icerik, 'plain', 'utf-8'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_ADRESIM, GMAIL_SIFREM)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Mail hatası: {e}")
        return False

@app.route('/')
def home():
    # Eğer bayi giriş yapmamışsa direkt giriş sayfasına gönder
    if 'bayi' not in session:
        return redirect(url_for('login'))
    
    urunler = verileri_getir()
    # Resim isimlerini sağlama alıyoruz
    for urun in urunler:
        if 'resim' in urun and urun['resim']:
            urun['resim'] = str(urun['resim']).strip().upper()
    
    return render_template('index.html', urunler=urunler, bayi=session['bayi'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        bayi_kodu = request.form.get('bayi_kodu')
        if bayi_kodu:
            session['bayi'] = bayi_kodu
            # Giriş başarılıysa ana sayfaya git
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/siparis_tamamla', methods=['POST'])
def siparis_tamamla():
    if 'bayi' not in session:
        return jsonify({"status": "error"}), 401
    veriler = request.json
    if siparis_maili_gonder(session['bayi'], veriler.get('sepet', '')):
        return jsonify({"status": "success"})
    return jsonify({"status": "mail_error"})

@app.route('/cikis')
def logout():
    session.clear() # Tüm oturumu temizle
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)