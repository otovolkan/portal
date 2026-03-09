from flask import Flask, render_template, request, session, redirect, url_for, jsonify, make_response
import pandas as pd
import os
import re
import json
import smtplib
import ssl
import git # GitHub otomatiği için gerekli kütüphane
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = "Oto959595-"
app.permanent_session_lifetime = timedelta(days=31)

# --- DOSYA YOLLARI (PORTAL KLASÖRÜNE GÖRE) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEPET_ARŞİVİ = os.path.join(BASE_DIR, 'sepet_kayitlari.json')
KUR_DOSYASI = os.path.join(BASE_DIR, 'kur.txt')
SIPARIS_LOG_DOSYASI = os.path.join(BASE_DIR, 'tum_siparisler.txt')

# --- YARDIMCI FONKSİYONLAR ---
def sepet_yukle_sunucudan():
    if not os.path.exists(SEPET_ARŞİVİ): return {}
    try:
        with open(SEPET_ARŞİVİ, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def sepet_kaydet_sunucuya(bayi_id, sepet):
    arsiv = sepet_yukle_sunucudan()
    arsiv[bayi_id] = sepet
    try:
        with open(SEPET_ARŞİVİ, 'w', encoding='utf-8') as f:
            json.dump(arsiv, f, ensure_ascii=False, indent=4)
    except: pass

def kur_oku():
    if not os.path.exists(KUR_DOSYASI): return 36.50
    try:
        with open(KUR_DOSYASI, 'r') as f:
            val = f.read().strip()
            return float(val) if val else 36.50
    except: return 36.50

def siparis_mail_at(bayi_adi, icerik):
    ALICILAR = ["info@otovolkan.com", "info@otovolkan.net"]
    GONDERICI = "voxoraku@gmail.com"
    SIFRE = "kjtu oxfh ojzl rsrk"
    try:
        msg = MIMEMultipart()
        msg['From'] = GONDERICI
        msg['To'] = ", ".join(ALICILAR)
        msg['Subject'] = f"B2B Siparis: {bayi_adi}"
        msg.attach(MIMEText(icerik, 'plain', 'utf-8'))
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=10) as server:
            server.login(GONDERICI, SIFRE)
            server.sendmail(GONDERICI, ALICILAR, msg.as_string())
        return True
    except Exception as e:
        print(f"MAIL HATASI: {str(e)}")
        return False

def fiyat_sayiya_cevir(deger):
    if not deger: return 0.0
    s = re.sub(r'[^\d,.]', '', str(deger))
    try:
        if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
        elif ',' in s: s = s.replace(',', '.')
        return float(s)
    except: return 0.0

def format_fiyat_birimli(sayi, birim):
    return f"{sayi:,.2f} {birim}".replace(',', 'X').replace('.', ',').replace('X', '.')

# --- AKILLI KOLİ İÇİ BELİRLEME ---
def koli_ici_belirle(item):
    # 1. Excel'deki koli miktarını yazdığın sütunu tara
    for k, v in item.items():
        if "koli" in str(k).lower():
            try:
                if v != "" and float(v) > 1: return int(float(v))
            except: pass

    # 2. Eğer sütunda yoksa ismin sonundaki (24) gibi parantezlere bak
    urun_adi = str(item.get('urun_adi', ''))
    matches = re.findall(r'\((\d+)\)', urun_adi)
    if matches:
        koli_miktari = int(matches[-1]) # En sondaki parantezi al (ML karışmasın)
        if koli_miktari > 1: return koli_miktari
            
    return 1

def verileri_yukle(sayfa_adi):
    path = os.path.join(BASE_DIR, 'urunler.xlsx')
    if not os.path.exists(path): return []
    try:
        df = pd.read_excel(path, sheet_name=sayfa_adi, engine='openpyxl')
        return df.fillna('').to_dict(orient='records')
    except: return []

# --- GITHUB OTOMATİK GÜNCELLEME ---
@app.route('/github_guncelle', methods=['POST'])
def github_guncelle():
    if request.method == 'POST':
        try:
            repo_path = "/home/otovolkan/portal"
            repo = git.Repo(repo_path)
            origin = repo.remotes.origin
            origin.pull()
            
            wsgi_file = "/var/www/otovolkan_pythonanywhere_com_wsgi.py"
            if os.path.exists(wsgi_file):
                os.utime(wsgi_file, None)
                
            return 'Guncelleme Tamam!', 200
        except Exception as e:
            return f'Hata: {str(e)}', 500
    return 'Gecersiz Metot', 400

# --- ROUTE'LAR ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        girilen_kod = str(request.form.get('bayi_kodu', '')).strip().lower()
        if girilen_kod == "admin95":
            session.clear()
            session.update({'giris_yapildi': True, 'bayi_adi': 'YÖNETİCİ', 'bayi_id': 'admin', 'admin_mi': True, 'iskonto': 0})
            return redirect(url_for('ana_sayfa'))
        bayiler = verileri_yukle('bayiler')
        bayi = next((b for b in bayiler if str(b.get('bayi_kodu','')).strip().lower() == girilen_kod), None)
        if bayi:
            iskonto_orani = 0
            for k, v in bayi.items():
                if "iskonto" in str(k).lower():
                    try: iskonto_orani = float(v) if v != "" else 0
                    except: iskonto_orani = 0
            bayi_id = str(bayi.get('bayi_kodu')).strip().upper()
            session.clear()
            session.update({'giris_yapildi': True, 'bayi_adi': bayi['bayi_adi'], 'bayi_id': bayi_id, 'admin_mi': False, 'iskonto': iskonto_orani})
            session[f'sepet_{bayi_id}'] = sepet_yukle_sunucudan().get(bayi_id, {})
            return redirect(url_for('ana_sayfa'))
    return render_template('login.html')

@app.route('/')
def ana_sayfa():
    if not session.get('giris_yapildi'): return redirect(url_for('login'))
    items = verileri_yukle('urunler')
    iskonto = session.get('iskonto', 0)
    guncel_kur = kur_oku()
    gecerli_urunler = []
    for item in items:
        u_no = str(item.get('urun_no', '')).upper()
        # Reklam/Kampanya filtrelemesini isteğe göre açıp kapatabilirsin
        # if "REKLAM" in u_no or "KAMPANYA" in u_no: continue
        
        ham_fiyat = fiyat_sayiya_cevir(item.get('fiyat'))
        marka_adi = str(item.get('marka', '')).upper()
        is_euro = ("BANNER" in marka_adi or "EURO" in str(item.get('para_birimi','')).upper())
        
        if is_euro:
            net_fiyat_tl = ham_fiyat * guncel_kur * (1 - (iskonto / 100))
        else:
            net_fiyat_tl = ham_fiyat * (1 - (iskonto / 100))
            
        item['fiyat_gosterim'] = format_fiyat_birimli(net_fiyat_tl, "TL")
        item['resim_temiz'] = str(item.get('resim', '')).strip()
        item['koli_ici'] = koli_ici_belirle(item)
        
        try:
            stok_val = str(item.get('stok', '0')).strip()
            item['stok_durumu'] = int(float(stok_val)) if stok_val and stok_val != 'nan' else 0
        except: item['stok_durumu'] = 0
        gecerli_urunler.append(item)
        
    markalar = sorted(list(set([str(u['marka']) for u in gecerli_urunler if u['marka']])))
    arama = request.args.get('search', '').lower()
    secili_marka = request.args.get('marka', '')
    urunler = [u for u in gecerli_urunler if (arama in str(u['urun_adi']).lower() or arama in str(u['urun_no']).lower()) and (not secili_marka or str(u['marka']) == secili_marka)]
    sepet_sayisi = sum(session.get(f"sepet_{session.get('bayi_id')}", {}).values())
    return render_template('index.html', urunler=urunler, markalar=markalar, sepet_sayisi=sepet_sayisi, bayi_adi=session['bayi_adi'], kur=guncel_kur, admin=session.get('admin_mi'), iskonto=iskonto)

@app.route('/sepetim')
def sepetim():
    if not session.get('giris_yapildi'): return redirect(url_for('login'))
    bayi_id = session.get('bayi_id')
    sepet = sepet_yukle_sunucudan().get(bayi_id, {})
    tum_urunler = verileri_yukle('urunler')
    iskonto = session.get('iskonto', 0)
    sepet_listesi, t_tl = [], 0
    guncel_kur = kur_oku()
    for u_no, adet in sepet.items():
        urun = next((u for u in tum_urunler if str(u['urun_no']) == u_no), None)
        if urun:
            ham_fiyat = fiyat_sayiya_cevir(urun.get('fiyat'))
            is_euro = ("BANNER" in str(urun.get('marka','')).upper() or "EURO" in str(urun.get('para_birimi','')).upper())
            if is_euro: net_birim_tl = ham_fiyat * guncel_kur * (1 - (iskonto / 100))
            else: net_birim_tl = ham_fiyat * (1 - (iskonto / 100))
            t_tl += (net_birim_tl * adet)
            k_ici = koli_ici_belirle(urun)
            u_copy = urun.copy()
            u_copy.update({'adet': adet, 'koli_ici': k_ici, 'koli_sayisi': adet // k_ici if k_ici > 1 else 0, 'kalan_adet': adet % k_ici if k_ici > 1 else 0, 'birim_gosterim': format_fiyat_birimli(net_birim_tl, "TL"), 'ara_toplam_gosterim': format_fiyat_birimli(net_birim_tl * adet, "TL")})
            sepet_listesi.append(u_copy)
    return render_template('sepet.html', sepet=sepet_listesi, toplam_tl=format_fiyat_birimli(t_tl, "TL"), kur=f"{guncel_kur:,.2f}".replace('.', ','), bayi_adi=session['bayi_adi'], wp_no="905335033019", iskonto=iskonto)

@app.route('/siparis_islem', methods=['POST'])
def siparis_islem():
    data = request.json
    bayi_id = session.get('bayi_id')
    bayi_adi = session.get('bayi_adi')
    mesaj_icerigi = data.get('mesaj', '')
    tarih_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    with open(SIPARIS_LOG_DOSYASI, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*50}\nTARIH: {tarih_str}\nBAYI: {bayi_adi}\nDETAY:\n{mesaj_icerigi}\n{'='*50}\n")
    if data.get('yontem') == 'email':
        siparis_mail_at(bayi_adi, mesaj_icerigi)
    sepet_kaydet_sunucuya(bayi_id, {})
    session[f'sepet_{bayi_id}'] = {}
    return jsonify({"durum": "ok"})

@app.route('/sepete_ekle/<urun_no>')
def sepete_ekle(urun_no):
    bayi_id = session.get('bayi_id')
    miktar = request.args.get('miktar', 1, type=int)
    sepet = session.get(f'sepet_{bayi_id}', {})
    sepet[str(urun_no)] = sepet.get(str(urun_no), 0) + miktar
    session[f'sepet_{bayi_id}'] = sepet
    sepet_kaydet_sunucuya(bayi_id, sepet)
    return redirect(request.referrer or url_for('ana_sayfa'))

@app.route('/sepet_sil/<urun_no>')
def sepet_sil(urun_no):
    bayi_id = session.get('bayi_id')
    sepet = session.get(f'sepet_{bayi_id}', {})
    if str(urun_no) in sepet: del sepet[str(urun_no)]
    session[f'sepet_{bayi_id}'] = sepet
    sepet_kaydet_sunucuya(bayi_id, sepet)
    return redirect(url_for('sepetim'))

@app.route('/kur_guncelle', methods=['POST'])
def kur_guncelle_route():
    with open(KUR_DOSYASI, 'w') as f: f.write(request.form.get('yeni_kur'))
    return redirect(url_for('ana_sayfa'))

@app.route('/cikis')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)