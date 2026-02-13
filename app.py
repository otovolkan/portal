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
def verileri_yukle():
    try:
        if not os.path.exists('urunler.xlsx'):
            return []
        df = pd.read_excel('urunler.xlsx', engine='openpyxl')
        df = df.fillna('')
        df.columns = [str(c).strip().lower() for c in df.columns]
        mapping = {'ürün adı': 'urun_adi', 'urun adi': 'urun_adi', 'adi': 'urun_adi', 'marka': 'marka', 'fiyat': 'fiyat', 'resim': 'resim'}
        df = df.rename(columns=mapping)
        urunler = df.to_dict(orient='records')
        for u in urunler:
            u['resim'] = str(u.get('resim', '')).strip().upper() # KAMPANYA1.PNG için büyük harf
        return urunler
    except Exception as e:
        print(f"Hata: {e}")
        return []

@app.route('/')
def home():
    if 'bayi' not in session:
        return redirect(url_for('login'))
    urunler = verileri_yukle()
    markalar = sorted(list(set([str(u.get('marka', '')) for u in urunler if u.get('marka')])))
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
    veriler = request.json
    sepet = veriler.get('sepet', '')
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_ADRESIM
        msg['To'] = GMAIL_ADRESIM
        msg['Subject'] = f"YENİ SİPARİŞ: {session['bayi']}"
        msg.attach(MIMEText(f"Bayi: {session['bayi']}\n\nSipariş:\n{sepet}", 'plain', 'utf-8'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_ADRESIM, GMAIL_SIFREM)
        server.send_message(msg)
        server.quit()
        return jsonify({"durum": "basarili"})
    except:
        return jsonify({"durum": "hata"})

@app.route('/cikis')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)