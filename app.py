from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import pandas as pd
import os
import re

app = Flask(__name__)
app.secret_key = "oTO959595-"

def verileri_yukle(sayfa_adi):
    if not os.path.exists('urunler.xlsx'): return []
    try:
        # engine='openpyxl' Render üzerinde en sağlam okuma yöntemidir
        df = pd.read_excel('urunler.xlsx', sheet_name=sayfa_adi, engine='openpyxl')
        return df.fillna('').to_dict(orient='records')
    except Exception as e:
        print(f"Hata: {e}")
        return []

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        girilen_kod = str(request.form.get('bayi_kodu', '')).strip().lower()
        bayiler = verileri_yukle('bayiler')
        
        bayi = None
        for b in bayiler:
            # Excel'deki sütun isminde boşluk olsa bile yakalamak için tüm anahtarları kontrol ediyoruz
            for key, value in b.items():
                if "bayi_kodu" in str(key).lower() and str(value).strip().lower() == girilen_kod:
                    bayi = b
                    break
            if bayi: break
            
        if bayi:
            session.clear() # 1900 hatasını ve eski oturumları temizler
            session.update({
                'giris_yapildi': True, 
                'bayi_adi': bayi.get('bayi_adi', 'Değerli Bayimiz'), 
                'sepet': {}
            })
            return redirect(url_for('ana_sayfa'))
    return render_template('login.html')

@app.route('/')
def ana_sayfa():
    if not session.get('giris_yapildi'): return redirect(url_for('login'))
    arama = request.args.get('search', '').lower()
    secili_marka = request.args.get('marka', '')
    items = verileri_yukle('urunler')
    
    reklamlar = [u for u in items if str(u.get('urun_no', '')).strip().upper().startswith('REKLAM')]
    markalar = sorted(list(set([str(u['marka']) for u in items if u['marka'] and not str(u.get('urun_no', '')).strip().upper().startswith('REKLAM')])))
    
    urunler = []
    arama_yapildi = (arama != '' or secili_marka != '')
    if arama_yapildi:
        urunler = [u for u in items if not str(u.get('urun_no', '')).strip().upper().startswith('REKLAM')]
        if arama:
            urunler = [u for u in urunler if arama in str(u['urun_adi']).lower() or arama in str(u['urun_no']).lower()]
        if secili_marka:
            urunler = [u for u in urunler if str(u['marka']) == secili_marka]
    
    sepet = session.get('sepet', {})
    sepet_sayisi = sum(sepet.values()) if sepet else 0
    return render_template('index.html', urunler=urunler, reklamlar=reklamlar, markalar=markalar, 
                           sepet_sayisi=sepet_sayisi, bayi_adi=session['bayi_adi'], 
                           secili_marka=secili_marka, arama_yapildi=arama_yapildi)

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
    for urun_no, adet in sepet.items():
        urun = next((u for u in tum_urunler if str(u['urun_no']) == urun_no), None)
        if urun:
            u_copy = urun.copy()
            u_copy['adet'] = adet
            sepet_listesi.append(u_copy)
    return render_template('sepet.html', sepet=sepet_listesi, bayi_adi=session['bayi_adi'])

@app.route('/sepet_sil/<urun_no>')
def sepet_sil(urun_no):
    if not session.get('giris_yapildi'): return redirect(url_for('login'))
    sepet = session.get('sepet', {})
    u_no = str(urun_no).strip()
    if u_no in sepet:
        del sepet[u_no]
        session['sepet'] = sepet
        session.modified = True
    return redirect(url_for('sepetim'))

@app.route('/cikis')
def cikis():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)