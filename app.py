from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import pandas as pd
import os
import re
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

app = Flask(__name__)
app.secret_key = "oTO959595-"

# --- GMAIL AYARLARI ---
GMAIL_ADRESIM = "voxoraku@gmail.com" 
GMAIL_SIFREM = "gpml fttc uzzu zvaa"

def verileri_yukle(sayfa_adi):
    if not os.path.exists('urunler.xlsx'): return []
    try:
        # Render'da hata almamak için engine='openpyxl' ekledik
        df = pd.read_excel('urunler.xlsx', sheet_name=sayfa_adi, engine='openpyxl')
        return df.fillna('').to_dict(orient='records')
    except Exception as e:
        print(f"Excel Okuma Hatası: {e}")
        return []

def siparis_maili_gonder(bayi_adi, sepet_detay):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_ADRESIM
        msg['To'] = GMAIL_ADRESIM
        msg['Subject'] = f"YENİ B2B SİPARİŞİ: {bayi_adi}"
        body = f"Sayın Yönetici,\n\n{bayi_adi} bayisinden yeni sipariş geldi.\n\nSipariş İçeriği:\n{sepet_detay}"
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_ADRESIM, GMAIL_SIFREM)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        girilen_kod = request.form['bayi_kodu'].strip().lower()
        bayiler = verileri_yukle('bayiler')
        bayi = next((b for b in bayiler if str(b['bayi_kodu']).strip().lower() == girilen_kod), None)
        if bayi:
            session.clear()
            session.update({'giris_yapildi': True, 'bayi_adi': bayi['bayi_adi'], 'sepet': {}})
            return redirect(url_for('ana_sayfa'))
    return render_template('login.html')

@app.route('/')
def ana_sayfa():
    if not session.get('giris_yapildi'): return redirect(url_for('login'))
    
    arama = request.args.get('search', '').lower()
    secili_marka = request.args.get('marka', '')
    
    items = verileri_yukle('urunler')
    
    # REKLAM1, REKLAM2, REKLAM3 gibi 'REKLAM' ile başlayan her şeyi yakalar
    reklamlar = [u for u in items if str(u.get('urun_no', '')).strip().upper().startswith('REKLAM')]
    
    # Markaları çekerken reklam satırlarını listeden çıkarıyoruz
    markalar = sorted(list(set([str(u['marka']) for u in items if u['marka'] and not str(u.get('urun_no', '')).strip().upper().startswith('REKLAM')])))
    
    urunler = []
    arama_yapildi = (arama != '' or secili_marka != '')

    if arama_yapildi:
        # Ürün aramalarında reklamları gösterme
        urunler = [u for u in items if not str(u.get('urun_no', '')).strip().upper().startswith('REKLAM')]
        if arama:
            urunler = [u for u in urunler if arama in str(u['urun_adi']).lower() or arama in str(u['urun_no']).lower()]
        if secili_marka:
            urunler = [u for u in urunler if str(u['marka']) == secili_marka]
    
    sepet_adet = sum(int(v) for v in session.get('sepet', {}).values())
    
    return render_template('index.html', urunler=urunler, reklamlar=reklamlar, markalar=markalar, 
                           sepet_sayisi=sepet_adet, bayi_adi=session['bayi_adi'], 
                           secili_marka=secili_marka, arama_yapildi=arama_yapildi)

@app.route('/sepete_ekle/<urun_no>')
def sepete_ekle(urun_no):
    sepet = session.get('sepet', {})
    sepet[str(urun_no)] = int(sepet.get(str(urun_no), 0)) + 1
    session['sepet'] = sepet
    return redirect(request.referrer or url_for('ana_sayfa'))

@app.route('/siparis_onayla', methods=['POST'])
def siparis_onayla():
    if not session.get('giris_yapildi'): return jsonify({"status": "error"}), 401
    veriler = request.json
    if siparis_maili_gonder(session['bayi_adi'], veriler.get('detay', '')):
        session['sepet'] = {}
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

@app.route('/cikis')
def cikis():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)