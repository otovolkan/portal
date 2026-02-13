from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = Flask(__name__)
# Bu anahtar oturumun (login durumunun) hafızada kalmasını sağlar
app.secret_key = 'Oto959595-'

# --- GMAIL AYARLARI ---
# Burayı kendi bilgilerine göre doldurmayı unutma ustam!
GMAIL_ADRESIM = "voxoraku@gmail.com" 
GMAIL_SIFREM = "gpml fttc uzzu zvaa" # Google'dan aldığın 16 haneli uygulama şifresi

def verileri_yukle():
    try:
        if os.path.exists('urunler.xlsx'):
            df = pd.read_excel('urunler.xlsx')
            # Excel'deki boş hücreleri temizle ki kod hata verip durmasın
            df = df.fillna('')
            # Sütun isimlerindeki boşlukları temizle ve küçük harf yap (Hata önleyici)
            df.columns = [c.strip().lower() for c in df.columns]
            
            urun_listesi = df.to_dict(orient='records')
            
            # Resim isimlerini büyük harfe çeviriyoruz ki KAMPANYA1.PNG ile eşleşsin
            for urun in urun_listesi:
                if 'resim' in urun and urun['resim'] != '':
                    urun['resim'] = str(urun['resim']).strip().upper()
                else:
                    urun['resim'] = 'YOK.PNG'
            return urun_listesi
        return []
    except Exception as e:
        print(f"Excel Okuma Hatası: {e}")
        return []

def siparis_maili_gonder(bayi_adi, sepet_detay):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_ADRESIM
        msg['To'] = GMAIL_ADRESIM # Sipariş kendi mailine gelsin
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

@app.route('/')
def home():
    # Bayi giriş yapmamışsa login sayfasına atar
    if 'bayi' not in session:
        return redirect(url_for('login'))
    
    urun_listesi = verileri_yukle()
    
    # Markaları Excel'den benzersiz olarak topla
    markalar = sorted(list(set([str(u.get('marka', '')) for u in urun_listesi if u.get('marka')])))
    
    return render_template('index.html', urunler=urun_listesi, bayi=session['bayi'], markalar=markalar)

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
        return jsonify({"durum": "hata", "mesaj": "Oturum kapalı"}), 401
    
    veriler = request.json
    sepet = veriler.get('sepet', '')
    
    if siparis_maili_gonder(session['bayi'], sepet):
        return jsonify({"durum": "basarili"})
    else:
        return jsonify({"durum": "hata", "mesaj": "Sipariş alındı ama mail iletilemedi."})

@app.route('/cikis')
def logout():
    # Tüm oturumu temizler ve giriş sayfasına atar
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)