import streamlit as st
import requests
import json
import re
import random
import time

# Sayfa Tasarımı
st.set_page_config(page_title="Google Forms Oto-Doldurucu", page_icon="📝", layout="centered")

st.title("📝 Google Forms Otomatik Doldurucu")
st.write("Anket linkini yapıştırın, sistem soruları ve seçenekleri otomatik tespit edip doldursun.")

# Kullanıcı Girdi Alanları
form_url = st.text_input("1. Google Anket Linki:", placeholder="https://docs.google.com/forms/d/e/.../viewform")

col1, col2 = st.columns(2)
with col1:
    total_responses = st.number_input("2. Kaç Yanıt Gönderilsin?", min_value=1, max_value=2000, value=420)
with col2:
    delay_seconds = st.number_input("3. Bekleme Süresi (Saniye):", min_value=0.1, max_value=60.0, value=0.3, step=0.1)

def parse_google_form(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        res_init = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
        clean_url = res_init.url.split('?')[0].replace('/closedform', '/viewform')
        if not clean_url.endswith('/viewform'):
            clean_url = clean_url.rsplit('/', 1)[0] + '/viewform'

        response = requests.get(clean_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None, None, f"Forma ulaşılamadı. (Durum Kodu: {response.status_code})"

        match = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(.*?);</script>', response.text, re.DOTALL)
        if not match:
            return None, None, "Form yapısı okunamadı. Anket kapalı olabilir."

        raw_data = json.loads(match.group(1))
        questions_raw = raw_data[1][1]
        
        form_structure = []
        for q in questions_raw:
            if not q or len(q) < 5 or not q[4]:
                continue
            
            question_text = q[1]
            entry_id = f"entry.{q[4][0][0]}"
            
            options = []
            if len(q[4][0]) > 1 and q[4][0][1]:
                options = [opt[0] for opt in q[4][0][1] if opt[0]]

            form_structure.append({
                "id": entry_id,
                "text": question_text,
                "options": options
            })

        response_url = clean_url.replace('/viewform', '/formResponse')
        return response_url, form_structure, None

    except Exception as e:
        return None, None, f"Hata oluştu: {str(e)}"

# Çalıştır Butonu
if st.button("🚀 Doldurmayı Başlat", type="primary", use_container_width=True):
    if not form_url:
        st.warning("Lütfen geçerli bir anket linki girin.")
    else:
        st.info("Anket yapısı analiz ediliyor...")
        response_url, form_structure, error = parse_google_form(form_url)

        if error:
            st.error(error)
        elif not form_structure:
            st.error("Ankette doldurulabilir soru bulunamadı.")
        else:
            st.success(f"Başarılı! Toplam {len(form_structure)} adet soru tespit edildi.")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            success_count = 0

            for i in range(1, total_responses + 1):
                payload = {}
                for q in form_structure:
                    if q['options']:
                        payload[q['id']] = random.choice(q['options'])
                    else:
                        payload[q['id']] = f"Test Yanıtı {i}"

                try:
                    res = requests.post(response_url, data=payload, timeout=5)
                    if res.status_code == 200:
                        success_count += 1
                except Exception:
                    pass

                progress = i / total_responses
                progress_bar.progress(progress)
                status_text.text(f"İlerleme: {i} / {total_responses} ({int(progress * 100)}%) - Başarılı: {success_count}")

                if i < total_responses:
                    time.sleep(delay_seconds)

            st.balloons()
            st.success(f"İşlem Tamamlandı! Toplam {success_count} adet yanıt gönderildi.")
