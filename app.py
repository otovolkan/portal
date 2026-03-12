from flask import Flask, render_template, request, session, redirect, url_for, jsonify, make_response
import pandas as pd
import os
import re
import json
import smtplib
import ssl
import git
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = "Oto959595-"
app.permanent_session_lifetime = timedelta(days=31)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEPET_ARŞİVİ = os.path.join(BASE_DIR, 'sepet_kayitlari.json')
KUR_DOSYASI = os.path.join(BASE_DIR, 'kur.txt')
SIPARIS_LOG_DOSYASI = os.path.join(BASE_DIR, 'tum_siparisler.txt')

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
    if not os.path.exists(KUR_DOSYASI): return 36.5000
    try:
        with open(KUR_DOSYASI, 'r') as f:
            val = f.read().strip()
            return float(val) if val else 36.5000
    except: return 36.5000

def fiyat_sayiya_cevir(deger):
    if not deger or pd.isna(deger): return 0.0
    s = re.sub(r'[^\d,.]', '', str(deger))
    try:
        if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
        elif ',' in s: s = s.replace(',', '.')
        return float(s)
    except: return 0.0

def format_fiyat_birimli(sayi, birim):
    return f"{sayi:,.2f} {birim}".replace(',', 'X').replace('.', ',').replace('X', '.')

# SADECE EXCEL'DEKİ KOLİ SÜTUNUNA BAKAR
def koli_ici_belirle(item):
    for k, v in item.items():
        if "koli" in str(k).lower():
            try:
                if v != "" and float(v) > 1: return int(float(v))
            except: pass
    return 1

def verileri_yukle(sayfa_adi):
    path = os.path.join(BASE_DIR, 'urunler.xlsx')
    if not os.path.exists(path): return []
    try:
        df = pd.read_excel(path, sheet_name=sayfa_adi, engine='openpyxl')
        return df.fillna('').to_dict(orient='records')
    except: return []

@app.route('/github_guncelle')
def github_guncelle():
    try:
        repo = git.Repo("/home/otovolkan/portal")
        repo.remotes.origin.pull()
        wsgi_file = "/var/www/otovolkan_pythonanywhere_com_wsgi.py"
        if os.path.exists(wsgi_file): os.utime(wsgi_file, None)
        return 'Tamam! Veriler ve Kodlar Guncellendi.', 200
    except Exception as e:
        return f'Hata: {str(e)}', 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        girilen_kod = str(request.form.get('bayi_kodu', '')).strip().lower()
        if girilen_kod == "admin95":
            session.clear()
            session.update({'giris_yapildi': True, 'bayi_adi': 'YÖNETİCİ', 'bayi_id': 'admin', 'admin_mi': True})
            return redirect(url_for('ana_sayfa'))
        bayiler = verileri_yukle('bayiler')
        bayi = next((b for b in bayiler if str(b.get('bayi_kodu','')).strip().lower() == girilen_kod), None)
        if bayi:
            bayi_id = str(bayi.get('bayi_kodu')).strip().upper()
            session.clear()
            session.update({'giris_yapildi': True, 'bayi_adi': bayi['bayi_adi'], 'bayi_id': bayi_id, 'admin_mi': False})
            return redirect(url_for('ana_sayfa'))
    return render_template('login.html')

@app.route('/')
def ana_sayfa():
    if not session.get('giris_yapildi'): return redirect(url_for('login'))
    bayi_id = session.get('bayi_id')
    bayi_iskonto = 0
    if not session.get('admin_mi'):
        bayiler = verileri_yukle('bayiler')
        guncel_bayi = next((b for b in bayiler if str(b.get('bayi_kodu','')).strip().upper() == bayi_id), None)
        if guncel_bayi:
            for k, v in guncel_bayi.items():
                if "iskonto" in str(k).lower():
                    try: bayi_iskonto = float(v) if v != "" else 0
                    except: bayi_iskonto = 0
    items = verileri_yukle('urunler')
    guncel_kur = kur_oku()
    gecerli_urunler, reklam_listesi = [], []
    arama = request.args.get('search', '').lower().strip()
    secili_marka = request.args.get('marka', '').strip()
    for item in items:
        u_no = str(item.get('urun_no', '')).upper()
        kategori_adi = str(item.get('KATEGORİ', '')).upper()
        if "REKLAM" in kategori_adi or "REKLAM" in u_no:
            item['resim_temiz'] = str(item.get('resim', '')).strip()
            reklam_listesi.append(item)
            continue
        if not arama and not secili_marka: continue
        liste_fiyat_ham = fiyat_sayiya_cevir(item.get('fiyat'))
        kampanya_orani = fiyat_sayiya_cevir(item.get('indirimli_fiyat'))
        marka_adi = str(item.get('marka', '')).upper()
        is_euro = ("BANNER" in marka_adi or "EURO" in str(item.get('para_birimi','')).upper())
        toplam_iskonto = bayi_iskonto + kampanya_orani
        if is_euro:
            liste_tl = liste_fiyat_ham * guncel_kur
            normal_net_tl = liste_tl * (1 - (bayi_iskonto / 100))
            son_net_tl = liste_tl * (1 - (toplam_iskonto / 100))
        else:
            liste_tl = liste_fiyat_ham
            normal_net_tl = liste_tl * (1 - (bayi_iskonto / 100))
            son_net_tl = liste_tl * (1 - (toplam_iskonto / 100))
        item['liste_fiyat_gosterim'] = format_fiyat_birimli(normal_net_tl, "TL")
        item['fiyat_gosterim'] = format_fiyat_birimli(son_net_tl, "TL")
        item['ozel_kampanya_var_mi'] = kampanya_orani > 0
        item['resim_temiz'] = str(item.get('resim', '')).strip()
        item['koli_ici'] = koli_ici_belirle(item)
        try:
            stok_val = str(item.get('stok', '0')).strip()
            item['stok_durumu'] = int(float(stok_val)) if stok_val and stok_val != 'nan' else 0
        except: item['stok_durumu'] = 0
        gecerli_urunler.append(item)
    all_items = verileri_yukle('urunler')
    markalar = sorted(list(set([str(u.get('marka', '')) for u in all_items if u.get('marka') and "REKLAM" not in str(u.get('KATEGORİ','')).upper()])))
    urunler = [u for u in gecerli_urunler if (arama in str(u['urun_adi']).lower() or arama in str(u['urun_no']).lower()) and (not secili_marka or str(u['marka']) == secili_marka)]
    sepet_sayisi = sum(sepet_yukle_sunucudan().get(bayi_id, {}).values())
    return render_template('index.html', urunler=urunler, reklamlar=reklam_listesi, markalar=markalar, sepet_sayisi=sepet_sayisi, bayi_adi=session['bayi_adi'], kur=guncel_kur, admin=session.get('admin_mi'), iskonto=bayi_iskonto)

@app.route('/sepetim')
def sepetim():
    if not session.get('giris_yapildi'): return redirect(url_for('login'))
    bayi_id = session.get('bayi_id')
    bayi_iskonto = 0
    if not session.get('admin_mi'):
        bayiler = verileri_yukle('bayiler')
        guncel_bayi = next((b for b in bayiler if str(b.get('bayi_kodu','')).strip().upper() == bayi_id), None)
        if guncel_bayi:
            for k, v in guncel_bayi.items():
                if "iskonto" in str(k).lower():
                    try: bayi_iskonto = float(v) if v != "" else 0
                    except: bayi_iskonto = 0
    sepet = sepet_yukle_sunucudan().get(bayi_id, {})
    tum_urunler = verileri_yukle('urunler')
    sepet_listesi, t_tl, guncel_kur = [], 0, kur_oku()
    for u_no, adet in sepet.items():
        urun = next((u for u in tum_urunler if str(u['urun_no']) == u_no), None)
        if urun:
            ham_fiyat = fiyat_sayiya_cevir(urun.get('fiyat'))
            kampanya_orani = fiyat_sayiya_cevir(urun.get('indirimli_fiyat'))
            toplam_iskonto = bayi_iskonto + kampanya_orani
            is_euro = ("BANNER" in str(urun.get('marka','')).upper() or "EURO" in str(urun.get('para_birimi','')).upper())
            if is_euro: net_birim_tl = ham_fiyat * guncel_kur * (1 - (toplam_iskonto / 100))
            else: net_birim_tl = ham_fiyat * (1 - (toplam_iskonto / 100))
            t_tl += (net_birim_tl * adet)
            k_ici = koli_ici_belirle(urun)
            u_copy = urun.copy()
            u_copy.update({'adet': adet, 'koli_ici': k_ici, 'koli_sayisi': adet // k_ici if k_ici > 1 else 0, 'kalan_adet': adet % k_ici if k_ici > 1 else 0, 'birim_gosterim': format_fiyat_birimli(net_birim_tl, "TL"), 'ara_toplam_gosterim': format_fiyat_birimli(net_birim_tl * adet, "TL")})
            sepet_listesi.append(u_copy)
    return render_template('sepet.html', sepet=sepet_listesi, toplam_tl=format_fiyat_birimli(t_tl, "TL"), kur=f"{guncel_kur:,.4f}".replace('.', ','), bayi_adi=session['bayi_adi'], wp_no="905335033019", iskonto=bayi_iskonto)

@app.route('/sepete_ekle/<urun_no>')
def sepete_ekle(urun_no):
    bayi_id = session.get('bayi_id')
    try:
        miktar = int(request.args.get('miktar', 1))
        if miktar < 1: miktar = 1
    except:
        miktar = 1
    sepet = sepet_yukle_sunucudan().get(bayi_id, {})
    sepet[str(urun_no)] = sepet.get(str(urun_no), 0) + miktar
    sepet_kaydet_sunucuya(bayi_id, sepet)
    return redirect(request.referrer or url_for('ana_sayfa'))

@app.route('/sepet_sil/<urun_no>')
def sepet_sil(urun_no):
    bayi_id = session.get('bayi_id')
    sepet = sepet_yukle_sunucudan().get(bayi_id, {})
    if str(urun_no) in sepet: del sepet[str(urun_no)]
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

if __name__ == '__main__': app.run(debug=True)