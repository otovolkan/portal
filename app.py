from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = Flask(__name__)
app.secret_key = 'Voxor_Oto_Volkan_B2B_2026_Ozel'

# --- GMAIL AYARLARI ---
GMAIL_ADRESIM = "senin_epostan@gmail.com" 
GMAIL_SIFREM = "xxxx xxxx xxxx xxxx" 

def verileri_getir():
    try:
        # Excel dosyasını oku
        df = pd.read_excel('urunler.xlsx')
        # Boş olan hücreleri boş metinle doldur ki kod hata vermesin
        df = df.fillna('') 
        
        urun_listesi = df.to_dict(orient='records')
        
        # Resim isimlerini sağlama alalım
        for urun in urun_listesi:
            if 'resim' in urun and urun['resim'] != '':
                # İsmi metne çevir, boşlukları sil ve büyük harf yap
                urun['resim'] = str(urun['resim']).strip().upper()
            else:
                # Resim yoksa varsayılan bir isim ata
                urun['resim'] = 'YOK.PNG'
                
        return urun_listesi
    except Exception as e:
        print(f"KRİTİK HATA (Excel okunamadı): {e}")
        return []

@app.route('/')
def home():
    # Giriş kontrolü
    if 'bayi' not in session:
        return redirect(url_for('login'))
    
    urunler = verileri_getir()
    
    # Eğer ürünler boş gelmişse terminale hata basar
    if not urunler:
        print("UYARI: Ürün listesi boş döndü!")

    # Markaları otomatik topla (Filtre menüsü için)
    markalar = sorted(list(set([u.get('marka', 'Diğer') for u in urunler if u.get('marka')])))
    
    return render_template('index.html', urunler=urunler, bayi=session['bayi'], markalar=markalar)

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
        return jsonify({"durum": "hata", "mesaj": "Oturum kapalı"}), 401
    
    veriler = request.json
    if siparis_maili_gonder(session['bayi'], veriler.get('sepet', '')):
        return jsonify({"durum": "basarili"})
    return jsonify({"durum": "hata"})

@app.route('/cikis')
def logout():
    session.clear()
    return redirect(url_for('login'))

def siparis_maili_gonder(bayi_adi, sepet_detay):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_ADRESIM
        msg['To'] = GMAIL_ADRESIM
        msg['Subject'] = f"SİPARİŞ: {bayi_adi}"
        msg.attach(MIMEText(f"Bayi: {bayi_adi}\n\nSipariş:\n{sepet_detay}", 'plain', 'utf-8'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_ADRESIM, GMAIL_SIFREM)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Mail hatası: {e}")
        return False

if __name__ == '__main__':
    app.run(debug=True)