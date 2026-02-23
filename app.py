from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import pandas as pd
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# HATA DÜZELTİLDİ: Flask(__name__) olarak güncellendi
app = Flask(__name__)
app.secret_key = "Oto959595-"

# --- AYARLAR: EMAIL VE WHATSAPP ---
SAYIN_USTA_TELEFON = "905335033019"  # WhatsApp numaran
MAIL_ADRESI = "voxoraku@gmail.com" # Gönderici mail
MAIL_SIFRESI = "gpml fttc uzzu zvaa" # Uygulama şifresi
ALICI_MAIL = "info@otovolkan.com" # Siparişin düşeceği mail

def format_fiyat(deger, para_birimi_kolonu="", marka=""):
    if not deger: return "0,00 TL"
    fiyat_str = str(deger).upper().strip()
    pb_kolon = str(para_birimi_kolonu).upper().strip()
    if pb_kolon in ["TL", "EURO", "TRY", "EUR", "€", "₺"]:
        birim = "EURO" if pb_kolon in ["EURO", "EUR", "€"] else "TL"
    elif "EURO" in fiyat_str or "€" in fiyat_str or "BANNER" in str(marka).upper():
        birim = "EURO"
    else: birim = "TL"
    
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
    
    bayi = session.get('bayi_adi', 'Bilinmeyen Bayi')
    tum_urunler = verileri_yukle('urunler')
    tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # EMAIL İÇİN TABLO OLUŞTURMA
    icerik = f"<h3>Yeni B2B Siparişi</h3><p><b>Bayi:</b> {bayi}</p><p><b>Tarih:</b> {tarih}</p><table border='1' cellpadding='5'><tr><th>Ürün No</th><th>Ürün Adı</th><th>Adet</th></tr>"
    for u_no, adet in sepet.items():
        urun = next((u for u in tum_urunler if str(u['urun_no']) == u_no), None)
        if urun: icerik += f"<tr><td>{u_no}</td><td>{urun['urun_adi']}</td><td>{adet}</td></tr>"
    icerik += "</table>"

    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_ADRESI
        msg['To'] = ALICI_MAIL
        msg['Subject'] = f"SİPARİŞ GELDİ - {bayi}"
        msg.attach(MIMEText(icerik, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(MAIL_ADRESI, MAIL_SIFRESI)
        server.send_message(msg)
        server.quit()
        
        session['sepet'] = {} # Başarılıysa sepeti temizle
        session.modified = True
        return jsonify({"mesaj": "Sipariş mail ile iletildi!"})
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

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