from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import pandas as pd
import os
import re
import smtplib
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(otovolkan)
app.secret_key = "Oto959595-"

# --- AYARLARINIZI BURADAN YAPIN ---
SAYIN_USTA_TELEFON = "905335033019"  # WhatsApp numaranız (Örn: 905321234567)
MAIL_ADRESI = "voxoraku@gmail.com"  # Gmail adresiniz
MAIL_SIFRESI = "gpml fttc uzzu zvaa"  # Gmail'den aldığınız 16 haneli Uygulama Şifresi
ALICI_MAIL = "info@otovolkan.com"   # Siparişlerin düşeceği e-posta adresi
SIPARIS_DOSYASI = 'siparisler.json'

def format_fiyat(deger, para_birimi_kolonu="", marka=""):
    if not deger: return "0,00 TL"
    fiyat_str = str(deger).upper().strip()
    pb_kolon = str(para_birimi_kolonu).upper().strip()
    
    if pb_kolon in ["TL", "EURO", "TRY", "EUR", "€", "₺"]:
        birim = "EURO" if pb_kolon in ["EURO", "EUR", "€"] else "TL"
    elif "EURO" in fiyat_str or "€" in fiyat_str or "BANNER" in str(marka).upper():
        birim = "EURO"
    else:
        birim = "TL"
    
    sayi_metin = re.sub(r'[^\d,.]', '', fiyat_str)
    try:
        if ',' in sayi_metin and '.' in sayi_metin:
            sayi = float(sayi_metin.replace('.', '').replace(',', '.'))
        elif ',' in sayi_metin:
            sayi = float(sayi_metin.replace(',', '.'))
        else:
            sayi = float(sayi_metin)
        return f"{sayi:,.2f} {birim}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return f"{deger} {birim}"

def fiyat_sayiya_cevir(deger):
    if not deger: return 0.0
    s = re.sub(r'[^\d,.]', '', str(deger))
    try:
        if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
        elif ',' in s: s = s.replace(',', '.')
        return float(s)
    except: return 0.0

def verileri_yukle(sayfa_adi):
    if not os.path.exists('urunler.xlsx'): return []
    try:
        df = pd.read_excel('urunler.xlsx', sheet_name=sayfa_adi, engine='openpyxl')
        return df.fillna('').to_dict(orient='records')
    except: return []

# SİPARİŞ VERİTABANI YÖNETİMİ
def siparisleri_yukle():
    if os.path.exists(SIPARIS_DOSYASI):
        with open(SIPARIS_DOSYASI, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def siparis_kaydet(yeni_siparis):
    siparisler = siparisleri_yukle()
    siparisler.append(yeni_siparis)
    with open(SIPARIS_DOSYASI, 'w', encoding='utf-8') as f:
        json.dump(siparisler, f, ensure_ascii=False, indent=4)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        girilen_kod = str(request.form.get('bayi_kodu', '')).strip().lower()
        bayiler = verileri_yukle('bayiler')
        bayi = next((b for b in bayiler if str(b.get('bayi_kodu','')).strip().lower() == girilen_kod), None)
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
    
    for item in items:
        pb = item.get('para_birimi', '')
        item['fiyat_gosterim'] = format_fiyat(item.get('fiyat'), para_birimi_kolonu=pb, marka=item.get('marka'))
        item['resim_temiz'] = str(item.get('resim', '')).strip()

    markalar = sorted(list(set([str(u['marka']) for u in items if u['marka'] and not str(u.get('urun_no', '')).strip().upper().startswith('REKLAM')])))
    urunler = [u for u in items if (arama in str(u['urun_adi']).lower() or arama in str(u['urun_no']).lower()) and (not secili_marka or str(u['marka']) == secili_marka)]
    
    sepet = session.get('sepet', {})
    sepet_sayisi = sum(sepet.values()) if sepet else 0
    return render_template('index.html', urunler=urunler, markalar=markalar, sepet_sayisi=sepet_sayisi, bayi_adi=session['bayi_adi'])

@app.route('/sepete_ekle/<urun_no>')
def sepete_ekle(urun_no):
    if not session.get('giris_yapildi'): return redirect(url_for('login'))
    sepet = session.get('sepet', {})
    sepet[str(urun_no)] = sepet.get(str(urun_no), 0) + 1
    session['sepet'] = sepet
    session.modified = True
    return redirect(request.referrer or url_for('ana_sayfa'))

@app.route('/sepetim')
def sepetim():
    if not session.get('giris_yapildi'): return redirect(url_for('login'))
    sepet = session.get('sepet', {})
    tum_urunler = verileri_yukle('urunler')
    sepet_listesi = []
    t_tl, t_euro = 0, 0
    for u_no, adet in sepet.items():
        urun = next((u for u in tum_urunler if str(u['urun_no']) == u_no), None)
        if urun:
            f_sayi = fiyat_sayiya_cevir(urun.get('fiyat'))
            ara_toplam = f_sayi * adet
            pb = str(urun.get('para_birimi', '')).upper()
            is_euro = (pb in ["EURO", "EUR", "€"] or "EURO" in str(urun.get('fiyat')).upper())
            if is_euro: t_euro += ara_toplam
            else: t_tl += ara_toplam
            
            u_copy = urun.copy()
            u_copy['adet'] = adet
            u_copy['birim_gosterim'] = format_fiyat(urun.get('fiyat'), para_birimi_kolonu=pb)
            u_copy['ara_toplam_gosterim'] = f"{ara_toplam:,.2f} {'EURO' if is_euro else 'TL'}".replace(',', 'X').replace('.', ',').replace('X', '.')
            sepet_listesi.append(u_copy)
            
    return render_template('sepet.html', sepet=sepet_listesi, 
                           toplam_tl=f"{t_tl:,.2f} TL".replace(',', 'X').replace('.', ',').replace('X', '.'),
                           toplam_euro=f"{t_euro:,.2f} EURO".replace(',', 'X').replace('.', ',').replace('X', '.'),
                           bayi_adi=session['bayi_adi'], wp_no=SAYIN_USTA_TELEFON)

@app.route('/siparis_tamamla', methods=['POST'])
def siparis_tamamla():
    if not session.get('giris_yapildi'): return jsonify({"hata": "Giriş gerekli"}), 403
    sepet = session.get('sepet', {})
    if not sepet: return jsonify({"hata": "Sepet boş"}), 400
    
    gecmis = siparisleri_yukle()
    s_no = f"B2B-{1000 + len(gecmis) + 1}"
    tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
    bayi = session['bayi_adi']
    
    tum_urunler = verileri_yukle('urunler')
    siparis_detay = []
    tablo_html = ""
    
    for u_no, adet in sepet.items():
        urun = next((u for u in tum_urunler if str(u['urun_no']) == u_no), None)
        if urun:
            siparis_detay.append({"no": u_no, "ad": urun['urun_adi'], "adet": adet})
            tablo_html += f"<tr><td>{u_no}</td><td>{urun['urun_adi']}</td><td>{adet} Adet</td></tr>"

    # Kayıt
    siparis_kaydet({"siparis_no": s_no, "bayi": bayi, "tarih": tarih, "urunler": siparis_detay})

    # Email
    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_ADRESI
        msg['To'] = ALICI_MAIL
        msg['Subject'] = f"Yeni Sipariş: {s_no} - {bayi}"
        html = f"<h3>Yeni B2B Siparişi</h3><p><b>No:</b> {s_no}<br><b>Bayi:</b> {bayi}<br><b>Tarih:</b> {tarih}</p><table border='1' cellpadding='5'><tr><th>No</th><th>Ürün Adı</th><th>Adet</th></tr>{tablo_html}</table>"
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(MAIL_ADRESI, MAIL_SIFRESI)
            server.send_message(msg)
    except:
        pass

    session['sepet'] = {} # Sepeti boşalt
    session.modified = True
    return jsonify({"mesaj": "Sipariş Alındı!", "siparis_no": s_no})

@app.route('/siparislerim')
def siparislerim():
    if not session.get('giris_yapildi'): return redirect(url_for('login'))
    tum_siparisler = siparisleri_yukle()
    bayi_siparisleri = [s for s in tum_siparisler if s['bayi'] == session['bayi_adi']]
    return render_template('siparisler.html', siparisler=bayi_siparisleri[::-1], bayi_adi=session['bayi_adi'])

@app.route('/sepet_sil/<urun_no>')
def sepet_sil(urun_no):
    sepet = session.get('sepet', {})
    if str(urun_no) in sepet:
        del sepet[str(urun_no)]
        session['sepet'] = sepet
        session.modified = True
    return redirect(url_for('sepetim'))

@app.route('/cikis')
def cikis():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)