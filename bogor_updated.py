import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import json
import os
import plotly.graph_objects as go
import plotly.express as px

# Konfigurasi halaman
st.set_page_config(
    page_title="EWS Longsor - Desa Petir Dramaga",
    page_icon="⚠️",
    layout="wide"
)

# CSS untuk styling simple dan elegan
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stAlert {
        border-radius: 10px;
    }
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .status-box {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 10px 0;
    }
    .status-aman {
        background-color: #d4edda;
        border: 2px solid #28a745;
        color: #155724;
    }
    .status-waspada {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
        color: #856404;
    }
    .status-bahaya {
        background-color: #f8d7da;
        border: 2px solid #dc3545;
        color: #721c24;
    }
    h1 {
        color: #2c3e50;
    }
    h3 {
        color: #34495e;
    }
    .notification-box {
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 4px solid #007bff;
        background-color: #e7f3ff;
    }
    .telegram-box {
        padding: 15px;
        border-radius: 8px;
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
        margin: 10px 0;
    }
    .subscriber-card {
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
        background-color: #f0f0f0;
        border-left: 3px solid #4caf50;
    }
    </style>
""", unsafe_allow_html=True)

# Inisialisasi session state
if 'historical_data' not in st.session_state:
    st.session_state.historical_data = []

if 'notifications' not in st.session_state:
    st.session_state.notifications = []

if 'last_status' not in st.session_state:
    st.session_state.last_status = "AMAN"

if 'telegram_log' not in st.session_state:
    st.session_state.telegram_log = []

# Koordinat Desa Petir, Dramaga, Bogor
LOCATION_LAT = -6.612778  # -6°36'46"S
LOCATION_LON = 106.725833  # 106°43'33"E

# Kode wilayah administrasi Desa Petir, Kec. Dramaga, Kab. Bogor
KODE_WILAYAH_ADM4 = "32.01.30.2005"

# ==================== KONFIGURASI TELEGRAM BOT ====================
TELEGRAM_BOT_TOKEN = "8271915231:AAGyCe7dKqbZMmrAs4_XHlfes-JaHNPJTeE"
SUBSCRIBERS_FILE = "telegram_subscribers.json"
TELEGRAM_ENABLED = True  # Aktifkan notifikasi Telegram
# ==================================================================

def load_subscribers():
    """Load daftar subscriber dari file JSON"""
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"subscribers": [], "metadata": {}}
    return {"subscribers": [], "metadata": {}}

def get_active_chat_ids():
    """Ambil semua Chat ID yang aktif"""
    data = load_subscribers()
    chat_ids = []
    for sub in data.get("subscribers", []):
        if sub.get("active", True):
            chat_ids.append(sub["chat_id"])
    return chat_ids

def send_telegram_message(message, parse_mode='HTML'):
    """
    Mengirim pesan ke semua subscriber yang terdaftar
    
    Args:
        message (str): Pesan yang akan dikirim
        parse_mode (str): Format pesan ('HTML' atau 'Markdown')
    
    Returns:
        bool: True jika berhasil, False jika gagal
    """
    if not TELEGRAM_ENABLED:
        return False
    
    if not TELEGRAM_BOT_TOKEN:
        st.session_state.telegram_log.append({
            'timestamp': datetime.now(),
            'status': 'error',
            'message': 'Token bot tidak diisi'
        })
        return False
    
    # Ambil Chat IDs dari file JSON
    chat_ids = get_active_chat_ids()
    
    if not chat_ids:
        st.session_state.telegram_log.append({
            'timestamp': datetime.now(),
            'status': 'warning',
            'message': 'Tidak ada subscriber aktif'
        })
        return False
    
    success_count = 0
    
    for chat_id in chat_ids:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                success_count += 1
                st.session_state.telegram_log.append({
                    'timestamp': datetime.now(),
                    'status': 'success',
                    'message': f'Pesan terkirim ke {chat_id}'
                })
            else:
                st.session_state.telegram_log.append({
                    'timestamp': datetime.now(),
                    'status': 'error',
                    'message': f'Gagal kirim ke {chat_id}: {response.status_code}'
                })
        
        except Exception as e:
            st.session_state.telegram_log.append({
                'timestamp': datetime.now(),
                'status': 'error',
                'message': f'Error ke {chat_id}: {str(e)}'
            })
    
    # Batasi log maksimal 20
    if len(st.session_state.telegram_log) > 20:
        st.session_state.telegram_log = st.session_state.telegram_log[-20:]
    
    return success_count > 0

def format_telegram_alert(status, weather_data):
    """
    Format pesan alert untuk Telegram dengan HTML
    
    Args:
        status (str): Status bahaya (AMAN/WASPADA/BAHAYA)
        weather_data (dict): Data cuaca dari BMKG
    
    Returns:
        str: Pesan terformat dalam HTML
    """
    icon_map = {
        'BAHAYA': '🔴',
        'WASPADA': '🟡',
        'AMAN': '🟢'
    }
    
    icon = icon_map.get(status, '⚪')
    
    message = f"""
<b>⚠️ PERINGATAN DINI LONGSOR</b>
<b>Desa Petir, Dramaga, Bogor</b>

{icon} <b>STATUS: {status}</b>

📊 <b>Data Cuaca Terkini:</b>
🌧️ Curah Hujan: {weather_data['curah_hujan']:.1f} mm/jam
💧 Kelembaban: {weather_data['kelembaban']:.1f}%
🌡️ Suhu: {weather_data['suhu']:.1f}°C
💨 Angin: {weather_data['kecepatan_angin']:.1f} km/jam ({weather_data['arah_angin']})
☁️ Kondisi: {weather_data['kondisi']}

📅 Waktu: {datetime.now().strftime('%d %B %Y, %H:%M:%S WIB')}
"""
    
    # Tambahkan rekomendasi sesuai status
    if status == "BAHAYA":
        message += """
<b>🚨 TINDAKAN SEGERA:</b>
• Segera evakuasi ke tempat aman
• Hubungi BPBD: (0251) 8324000
• Jauhi lereng dan tebing
• Siapkan tas darurat
"""
    elif status == "WASPADA":
        message += """
<b>⚠️ TINDAKAN:</b>
• Tetap siaga dan pantau cuaca
• Siapkan rencana evakuasi
• Perhatikan tanda-tanda longsor
• Hindari aktivitas di lereng
"""
    else:
        message += """
<b>✅ TINDAKAN:</b>
• Kondisi normal
• Tetap waspada
• Lakukan pemeriksaan rutin drainase
"""
    
    message += f"\n📍 Lokasi: {LOCATION_LAT:.6f}°S, {LOCATION_LON:.6f}°E"
    
    return message

def send_status_alert(status, weather_data):
    """
    Kirim notifikasi alert status ke Telegram
    
    Args:
        status (str): Status bahaya
        weather_data (dict): Data cuaca
    
    Returns:
        bool: True jika berhasil
    """
    message = format_telegram_alert(status, weather_data)
    return send_telegram_message(message)

def send_periodic_report(weather_data, tingkat_bahaya):
    """
    Kirim laporan berkala ke Telegram
    
    Args:
        weather_data (dict): Data cuaca
        tingkat_bahaya (str): Status bahaya
    """
    icon_map = {
        'BAHAYA': '🔴',
        'WASPADA': '🟡',
        'AMAN': '🟢'
    }
    
    icon = icon_map.get(tingkat_bahaya, '⚪')
    
    message = f"""
<b>📊 LAPORAN BERKALA EWS</b>
<b>Desa Petir, Dramaga</b>

{icon} Status: {tingkat_bahaya}

<b>Data Cuaca:</b>
🌧️ {weather_data['curah_hujan']:.1f} mm/jam
💧 {weather_data['kelembaban']:.1f}%
🌡️ {weather_data['suhu']:.1f}°C
💨 {weather_data['kecepatan_angin']:.1f} km/jam
☁️ {weather_data['kondisi']}

📅 {datetime.now().strftime('%d/%m/%Y %H:%M WIB')}
"""
    
    return send_telegram_message(message)

# Fungsi untuk mendapatkan data cuaca dari BMKG API
@st.cache_data(ttl=600)
def get_bmkg_weather_data():
    """
    Mengambil data cuaca real-time dari BMKG API Publik
    Endpoint: https://api.bmkg.go.id/publik/prakiraan-cuaca
    """
    try:
        url = f"https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={KODE_WILAYAH_ADM4}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            lokasi = data.get('lokasi', {})
            cuaca_data = data.get('data', [])
            
            if cuaca_data and len(cuaca_data) > 0:
                cuaca_lokasi = cuaca_data[0].get('cuaca', [[]])[0]
                
                if cuaca_lokasi and len(cuaca_lokasi) > 0:
                    cuaca_sekarang = cuaca_lokasi[0]
                    
                    arah_angin_map = {
                        'N': 'Utara', 'NE': 'Timur Laut', 'E': 'Timur',
                        'SE': 'Tenggara', 'S': 'Selatan', 'SW': 'Barat Daya',
                        'W': 'Barat', 'NW': 'Barat Laut'
                    }
                    
                    suhu = cuaca_sekarang.get('t', 25)
                    kelembaban = cuaca_sekarang.get('hu', 75)
                    kecepatan_angin = cuaca_sekarang.get('ws', 10)
                    arah_angin_code = cuaca_sekarang.get('wd', 'N')
                    arah_angin = arah_angin_map.get(arah_angin_code, arah_angin_code)
                    kondisi = cuaca_sekarang.get('weather_desc', 'Berawan')
                    curah_hujan_mm = cuaca_sekarang.get('tp', 0)
                    
                    curah_hujan = curah_hujan_mm / 3 if curah_hujan_mm > 0 else 0
                    
                    if curah_hujan == 0:
                        kondisi_lower = kondisi.lower()
                        if 'lebat' in kondisi_lower or 'petir' in kondisi_lower:
                            curah_hujan = 55.0
                        elif 'hujan' in kondisi_lower and 'ringan' not in kondisi_lower:
                            curah_hujan = 30.0
                        elif 'ringan' in kondisi_lower:
                            curah_hujan = 15.0
                    
                    return {
                        'status': 'success',
                        'curah_hujan': round(curah_hujan, 1),
                        'kelembaban': round(kelembaban, 1),
                        'suhu': round(suhu, 1),
                        'kecepatan_angin': round(kecepatan_angin, 1),
                        'kondisi': kondisi,
                        'tekanan_udara': 1013.0,
                        'arah_angin': arah_angin,
                        'waktu_update': cuaca_sekarang.get('local_datetime', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                        'lokasi': f"{lokasi.get('desa', 'Petir')}, {lokasi.get('kecamatan', 'Dramaga')}, {lokasi.get('kotkab', 'Kab. Bogor')}"
                    }
            
            return {
                'status': 'partial',
                'message': 'Data tidak lengkap dari BMKG',
                'curah_hujan': 0,
                'kelembaban': 75,
                'suhu': 25,
                'kecepatan_angin': 10,
                'kondisi': 'Berawan',
                'tekanan_udara': 1013.0,
                'arah_angin': 'Utara',
                'lokasi': 'Desa Petir, Dramaga'
            }
        
        elif response.status_code == 404:
            return {
                'status': 'error',
                'message': f'Kode wilayah {KODE_WILAYAH_ADM4} tidak ditemukan di database BMKG'
            }
        else:
            return {
                'status': 'error',
                'message': f'HTTP Error {response.status_code} dari server BMKG'
            }
            
    except requests.exceptions.Timeout:
        return {
            'status': 'error',
            'message': 'Timeout - Server BMKG tidak merespon dalam 15 detik'
        }
    except requests.exceptions.RequestException as e:
        return {
            'status': 'error',
            'message': f'Connection Error: {str(e)}'
        }
    except json.JSONDecodeError as e:
        return {
            'status': 'error',
            'message': f'JSON Parse Error: Response bukan format JSON yang valid'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected Error: {str(e)}'
        }

def hitung_tingkat_bahaya(curah_hujan, kelembaban):
    """Menghitung tingkat bahaya longsor"""
    if curah_hujan > 50 and kelembaban > 85:
        return "BAHAYA", "🔴"
    elif curah_hujan > 20 or kelembaban > 80:
        return "WASPADA", "🟡"
    else:
        return "AMAN", "🟢"

def add_notification(status, message):
    """Menambahkan notifikasi baru"""
    notification = {
        'timestamp': datetime.now(),
        'status': status,
        'message': message
    }
    st.session_state.notifications.insert(0, notification)
    if len(st.session_state.notifications) > 10:
        st.session_state.notifications = st.session_state.notifications[:10]

def save_historical_data(weather_data, tingkat_bahaya):
    """Menyimpan data cuaca ke historis"""
    data_point = {
        'timestamp': datetime.now(),
        'curah_hujan': weather_data['curah_hujan'],
        'kelembaban': weather_data['kelembaban'],
        'suhu': weather_data['suhu'],
        'status': tingkat_bahaya
    }
    st.session_state.historical_data.append(data_point)
    
    if len(st.session_state.historical_data) > 144:
        st.session_state.historical_data = st.session_state.historical_data[-144:]

# Header
st.title("⚠️ Sistem Peringatan Dini Longsor")
st.subheader("Desa Petir, Kecamatan Dramaga, Kabupaten Bogor")

# Waktu update dan tombol kontrol
col_time1, col_time2, col_time3, col_time4 = st.columns([2, 1, 1, 1])
with col_time1:
    st.caption(f"📅 Terakhir diperbarui: {datetime.now().strftime('%d %B %Y, %H:%M:%S WIB')}")
with col_time2:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
with col_time3:
    if st.button("🔔 Notifikasi"):
        st.session_state.show_notifications = not st.session_state.get('show_notifications', False)
with col_time4:
    if st.button("📱 Telegram"):
        st.session_state.show_telegram = not st.session_state.get('show_telegram', False)

st.divider()

# Ambil data cuaca
with st.spinner("🌐 Mengambil data cuaca real-time dari BMKG..."):
    weather_data = get_bmkg_weather_data()

if weather_data['status'] in ['success', 'partial']:
    # Hitung tingkat bahaya
    tingkat_bahaya, icon = hitung_tingkat_bahaya(
        weather_data['curah_hujan'], 
        weather_data['kelembaban']
    )
    
    # Simpan data historis
    save_historical_data(weather_data, tingkat_bahaya)
    
    # Cek perubahan status dan kirim notifikasi
    if st.session_state.last_status != tingkat_bahaya:
        notif_msg = ""
        if tingkat_bahaya == "BAHAYA":
            notif_msg = "⚠️ STATUS BERUBAH KE BAHAYA! Segera lakukan evakuasi!"
            add_notification("BAHAYA", notif_msg)
        elif tingkat_bahaya == "WASPADA":
            notif_msg = "⚠️ Status berubah ke WASPADA. Tetap siaga dan pantau perkembangan."
            add_notification("WASPADA", notif_msg)
        else:
            notif_msg = "✅ Status kembali aman. Tetap waspada."
            add_notification("AMAN", notif_msg)
        
        # Kirim alert ke Telegram saat status berubah
        if TELEGRAM_ENABLED:
            send_status_alert(tingkat_bahaya, weather_data)
        
        st.session_state.last_status = tingkat_bahaya
    
    # Warning jika data partial
    if weather_data['status'] == 'partial':
        st.warning(f"⚠️ {weather_data.get('message', 'Data tidak lengkap')}")
    
    # Tampilkan log Telegram jika diminta
    if st.session_state.get('show_telegram', False):
        with st.expander("📱 Telegram Bot Management", expanded=True):
            if TELEGRAM_ENABLED:
                # Load subscriber data
                subscriber_data = load_subscribers()
                subscribers = subscriber_data.get("subscribers", [])
                total_subscribers = len(subscribers)
                
                st.markdown("### 🤖 Status Bot & Subscribers")
                
                col_tg1, col_tg2, col_tg3 = st.columns(3)
                
                with col_tg1:
                    st.metric("👥 Total Subscribers", total_subscribers)
                
                with col_tg2:
                    active_subs = len([s for s in subscribers if s.get('active', True)])
                    st.metric("✅ Aktif", active_subs)
                
                with col_tg3:
                    if subscriber_data.get('metadata', {}).get('last_update'):
                        last_update = datetime.fromisoformat(subscriber_data['metadata']['last_update'])
                        st.caption(f"Update: {last_update.strftime('%H:%M:%S')}")
                
                st.divider()
                
                # Daftar Subscribers
                st.markdown("### 📋 Daftar Subscribers")
                
                if subscribers:
                    for i, sub in enumerate(subscribers, 1):
                        col1, col2, col3 = st.columns([3, 2, 1])
                        
                        with col1:
                            name = sub.get('first_name', 'Unknown')
                            username = sub.get('username', 'N/A')
                            st.markdown(f"""
                                <div class="subscriber-card">
                                    <strong>#{i}. {name}</strong><br>
                                    <small>@{username} | ID: <code>{sub['chat_id']}</code></small>
                                </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            reg_date = datetime.fromisoformat(sub.get('registered_at', datetime.now().isoformat()))
                            st.caption(f"📅 {reg_date.strftime('%d/%m/%Y %H:%M')}")
                        
                        with col3:
                            status_icon = "✅" if sub.get('active', True) else "❌"
                            st.markdown(f"<h3 style='text-align: center;'>{status_icon}</h3>", unsafe_allow_html=True)
                else:
                    st.info("📭 Belum ada subscriber. Minta user untuk /start di bot Telegram.")
                
                st.divider()
                
                # Control Panel
                st.markdown("### 🎛️ Control Panel")
                
                col_cp1, col_cp2, col_cp3 = st.columns(3)
                
                with col_cp1:
                    if st.button("📤 Kirim Test Pesan", use_container_width=True):
                        test_msg = f"""
<b>🧪 TEST PESAN</b>
Dashboard EWS Longsor Desa Petir

Status: {tingkat_bahaya}
Waktu: {datetime.now().strftime('%H:%M:%S')}

Pesan ini adalah test notifikasi.
"""
                        if send_telegram_message(test_msg):
                            st.success(f"✅ Pesan terkirim ke {total_subscribers} subscriber!")
                        else:
                            st.error("❌ Gagal mengirim pesan")
                
                with col_cp2:
                    if st.button("📊 Kirim Laporan", use_container_width=True):
                        if send_periodic_report(weather_data, tingkat_bahaya):
                            st.success(f"✅ Laporan terkirim ke {total_subscribers} subscriber!")
                        else:
                            st.error("❌ Gagal mengirim laporan")
                
                with col_cp3:
                    if st.button("🔄 Reload Subscribers", use_container_width=True):
                        st.rerun()
                
                st.divider()
                
                # Log Pengiriman
                st.markdown("### 📜 Log Pengiriman Pesan")
                if st.session_state.telegram_log:
                    for log in st.session_state.telegram_log[:10]:
                        status_icon = "✅" if log['status'] == 'success' else "❌" if log['status'] == 'error' else "⚠️"
                        st.caption(f"{status_icon} {log['timestamp'].strftime('%H:%M:%S')} - {log['message']}")
                else:
                    st.info("📭 Belum ada log pengiriman")
                
                st.divider()
                
                # Informasi Bot
                st.markdown("### ℹ️ Cara Menggunakan")
                st.info("""
**Untuk User/Subscriber:**
1. Buka Telegram dan cari bot Anda
2. Ketik `/start` untuk mendaftar
3. Anda akan otomatis menerima notifikasi
4. Gunakan `/status` untuk cek registrasi
5. Gunakan `/stop` untuk berhenti berlangganan

**Command Bot:**
- `/start` - Daftar notifikasi
- `/stop` - Berhenti notifikasi  
- `/status` - Cek status registrasi
- `/info` - Info sistem EWS
- `/help` - Panduan lengkap

**File Subscribers:**
- Lokasi: `telegram_subscribers.json`
- Auto-update saat ada yang /start atau /stop
- Bot listener harus running 24/7
                """)
                
            else:
                st.warning("""
                **⚠️ Telegram Bot Tidak Aktif**
                
                Untuk mengaktifkan notifikasi Telegram:
                1. Buat bot di @BotFather
                2. Dapatkan Bot Token
                3. Isi variabel di kode:
                   - `TELEGRAM_BOT_TOKEN`
                   - `TELEGRAM_ENABLED = True`
                4. Jalankan `telegram_bot_listener.py`
                5. User tinggal /start di bot
                """)
    
    # Tampilkan notifikasi jika diminta
    if st.session_state.get('show_notifications', False):
        with st.expander("🔔 Notifikasi Terbaru", expanded=True):
            if st.session_state.notifications:
                for notif in st.session_state.notifications[:5]:
                    st.markdown(f"""
                        <div class="notification-box">
                            <strong>{notif['timestamp'].strftime('%H:%M:%S')}</strong> - {notif['message']}
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Belum ada notifikasi")
    
    # Status Peringatan
    status_class = f"status-{tingkat_bahaya.lower()}"
    st.markdown(f"""
        <div class="status-box {status_class}">
            <h1>{icon} STATUS: {tingkat_bahaya}</h1>
            <h3>{weather_data['kondisi']}</h3>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Metrics dalam 2 baris
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🌧️ Curah Hujan",
            value=f"{weather_data['curah_hujan']:.1f} mm/jam",
            delta="Tinggi" if weather_data['curah_hujan'] > 30 else "Normal",
            delta_color="inverse" if weather_data['curah_hujan'] > 30 else "normal"
        )
    
    with col2:
        st.metric(
            label="💧 Kelembaban",
            value=f"{weather_data['kelembaban']:.1f}%",
            delta="Tinggi" if weather_data['kelembaban'] > 80 else "Normal",
            delta_color="inverse" if weather_data['kelembaban'] > 80 else "normal"
        )
    
    with col3:
        st.metric(
            label="🌡️ Suhu",
            value=f"{weather_data['suhu']:.1f}°C"
        )
    
    with col4:
        st.metric(
            label="💨 Kec. Angin",
            value=f"{weather_data['kecepatan_angin']:.1f} km/jam"
        )
    
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric(
            label="🧭 Arah Angin",
            value=weather_data.get('arah_angin', 'N/A')
        )
    
    with col6:
        st.metric(
            label="📊 Tekanan Udara",
            value=f"{weather_data.get('tekanan_udara', 1013):.1f} hPa"
        )
    
    with col7:
        risk_score = min(100, int((weather_data['curah_hujan']/70 * 50) + (weather_data['kelembaban']/100 * 50)))
        st.metric(
            label="⚠️ Tingkat Risiko",
            value=f"{risk_score}%"
        )
    
    with col8:
        # Tampilkan jumlah subscribers
        subscriber_count = len(get_active_chat_ids())
        st.metric(
            label="👥 Subscribers",
            value=subscriber_count
        )
    
    # Info lokasi dan waktu update
    st.caption(f"📍 Lokasi: {weather_data.get('lokasi', 'Desa Petir, Dramaga')}")
    if 'waktu_update' in weather_data:
        st.caption(f"🕐 Data BMKG: {weather_data['waktu_update']}")
    
    st.divider()
    
    # Grafik Historis
    st.subheader("📊 Grafik Monitoring Real-time")
    
    if len(st.session_state.historical_data) > 1:
        df_hist = pd.DataFrame(st.session_state.historical_data)
        
        tab1, tab2, tab3 = st.tabs(["📈 Curah Hujan & Kelembaban", "🌡️ Suhu", "📊 Status Bahaya"])
        
        with tab1:
            fig1 = go.Figure()
            
            fig1.add_trace(go.Scatter(
                x=df_hist['timestamp'],
                y=df_hist['curah_hujan'],
                name='Curah Hujan (mm/jam)',
                line=dict(color='#3498db', width=2),
                fill='tozeroy',
                fillcolor='rgba(52, 152, 219, 0.2)'
            ))
            
            fig1.add_trace(go.Scatter(
                x=df_hist['timestamp'],
                y=df_hist['kelembaban'],
                name='Kelembaban (%)',
                line=dict(color='#9b59b6', width=2),
                yaxis='y2'
            ))
            
            fig1.add_hline(y=50, line_dash="dash", line_color="red", 
                          annotation_text="Threshold Bahaya (50mm)", 
                          annotation_position="right")
            fig1.add_hline(y=20, line_dash="dash", line_color="orange", 
                          annotation_text="Threshold Waspada (20mm)", 
                          annotation_position="right")
            
            fig1.update_layout(
                title="Monitoring Curah Hujan dan Kelembaban",
                xaxis_title="Waktu",
                yaxis_title="Curah Hujan (mm/jam)",
                yaxis2=dict(
                    title="Kelembaban (%)",
                    overlaying='y',
                    side='right'
                ),
                hovermode='x unified',
                height=400,
                plot_bgcolor='#f8f9fa',
                paper_bgcolor='white'
            )
            
            st.plotly_chart(fig1, use_container_width=True)
        
        with tab2:
            fig2 = go.Figure()
            
            fig2.add_trace(go.Scatter(
                x=df_hist['timestamp'],
                y=df_hist['suhu'],
                name='Suhu (°C)',
                line=dict(color='#e74c3c', width=3),
                mode='lines+markers'
            ))
            
            fig2.update_layout(
                title="Monitoring Suhu Udara",
                xaxis_title="Waktu",
                yaxis_title="Suhu (°C)",
                hovermode='x unified',
                height=400,
                plot_bgcolor='#f8f9fa',
                paper_bgcolor='white'
            )
            
            st.plotly_chart(fig2, use_container_width=True)
        
        with tab3:
            status_counts = df_hist['status'].value_counts()
            
            colors = {
                'AMAN': '#28a745',
                'WASPADA': '#ffc107',
                'BAHAYA': '#dc3545'
            }
            
            fig3 = go.Figure(data=[go.Pie(
                labels=status_counts.index,
                values=status_counts.values,
                marker=dict(colors=[colors.get(s, '#cccccc') for s in status_counts.index]),
                hole=0.4
            )])
            
            fig3.update_layout(
                title="Distribusi Status Bahaya (Historical)",
                height=400
            )
            
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("📊 Data historis akan muncul setelah beberapa kali refresh")
    
    st.divider()
    
    # Peta Lokasi
    st.subheader("🗺️ Lokasi Pemantauan - Desa Petir, Dramaga")
    
    map_data = pd.DataFrame({
        'lat': [LOCATION_LAT],
        'lon': [LOCATION_LON],
        'name': ['Desa Petir, Dramaga'],
        'status': [tingkat_bahaya]
    })
    
    map_data['color'] = map_data['status'].map({
        'AMAN': '#28a745',
        'WASPADA': '#ffc107',
        'BAHAYA': '#dc3545'
    })
    
    fig_map = go.Figure(go.Scattermapbox(
        lat=map_data['lat'],
        lon=map_data['lon'],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=20,
            color=map_data['color']
        ),
        text=map_data['name'],
        hovertemplate='<b>%{text}</b><br>Status: ' + tingkat_bahaya + '<br>Lat: ' + f'{LOCATION_LAT:.6f}' + '<br>Lon: ' + f'{LOCATION_LON:.6f}' + '<extra></extra>'
    ))
    
    fig_map.update_layout(
        mapbox_style="open-street-map",
        mapbox=dict(
            center=dict(lat=LOCATION_LAT, lon=LOCATION_LON),
            zoom=13
        ),
        height=400,
        margin={"r":0,"t":0,"l":0,"b":0}
    )
    
    st.plotly_chart(fig_map, use_container_width=True)
    
    st.caption(f"📍 Koordinat: {LOCATION_LAT:.6f}°S, {LOCATION_LON:.6f}°E | Kode Wilayah: {KODE_WILAYAH_ADM4}")
    
    st.divider()
    
    # Rekomendasi berdasarkan status
    st.subheader("📋 Rekomendasi Tindakan")
    
    if tingkat_bahaya == "BAHAYA":
        st.error("""
        **⚠️ BAHAYA - SEGERA EVAKUASI!**
        - 🚨 Segera evakuasi ke tempat aman yang lebih tinggi
        - 📞 Hubungi pihak berwenang dan tim SAR
        - 🏔️ Jauhi lereng dan tebing
        - 🎒 Siapkan tas darurat dan dokumen penting
        - 📻 Pantau informasi dari petugas setempat
        - 👥 Bantu warga yang memerlukan bantuan evakuasi
        """)
    elif tingkat_bahaya == "WASPADA":
        st.warning("""
        **⚠️ WASPADA - TETAP SIAGA!**
        - 📡 Pantau perkembangan cuaca secara berkala
        - 🎒 Siapkan rencana evakuasi dan tas darurat
        - 👀 Perhatikan tanda-tanda longsor (retakan tanah, air keruh)
        - ⛰️ Hindari aktivitas di dekat lereng
        - 💬 Tetap berkomunikasi dengan warga sekitar
        - 🔦 Siapkan penerangan dan alat komunikasi darurat
        """)
    else:
        st.success("""
        **✅ AMAN - KONDISI NORMAL**
        - ☁️ Kondisi cuaca dalam batas normal
        - 👁️ Tetap waspada terhadap perubahan cuaca
        - 🔧 Lakukan pemeriksaan rutin drainase
        - 🧹 Jaga kebersihan saluran air
        - 📚 Edukasi masyarakat tentang mitigasi bencana
        """)
    
    st.divider()
    
    # Informasi kontak darurat
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📞 Kontak Darurat")
        st.info("**BPBD Kab. Bogor**\n☎️ (0251) 8324000\n📱 0812-1010-9002")
        st.info("**SAR Nasional**\n☎️ 115")
        st.info("**BMKG Bogor**\n☎️ (0251) 8311511")
    
    with col2:
        st.subheader("🏥 Layanan Kesehatan")
        st.info("**PMI Bogor**\n☎️ (0251) 8321111")
        st.info("**Ambulans**\n☎️ 118 / 119")
        st.info("**Kec. Dramaga**\n☎️ (0251) 8623002")

else:
    st.error(f"❌ Gagal mengambil data dari BMKG API")
    st.warning(f"**Detail Error:** {weather_data.get('message', 'Unknown error')}")
    
    # Troubleshooting info
    with st.expander("🔧 Troubleshooting & Informasi"):
        st.markdown(f"""
        **Endpoint yang digunakan:**
        ```
        https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={KODE_WILAYAH_ADM4}
        ```
        
        **Kemungkinan Penyebab:**
        1. ❌ Kode wilayah ADM4 tidak valid atau tidak terdaftar di BMKG
        2. 🔧 Server BMKG sedang maintenance
        3. 🌐 Koneksi internet tidak stabil
        4. ⏰ Timeout (lebih dari 15 detik)
        5. 📊 Format response dari BMKG berubah
        
        **Solusi:**
        - Pastikan koneksi internet stabil
        - Coba refresh beberapa saat lagi
        - Data BMKG diupdate setiap 3 jam
        - Hubungi admin jika masalah berlanjut
        
        **Informasi Teknis:**
        - Kode Wilayah: `{KODE_WILAYAH_ADM4}`
        - Lokasi: Desa Petir, Kec. Dramaga, Kab. Bogor
        - Koordinat: {LOCATION_LAT:.6f}°S, {LOCATION_LON:.6f}°E
        
        **Alternatif:**
        Jika kode wilayah tidak valid, coba cek di:
        - https://data.bmkg.go.id/prakiraan-cuaca/
        - Keputusan Mendagri No. 050-145 Tahun 2022
        """)

# Footer
st.divider()
st.caption("📡 Data real-time dari BMKG API Publik (api.bmkg.go.id)")
st.caption("🌐 Sumber Resmi: https://data.bmkg.go.id/prakiraan-cuaca/")
st.caption("⚠️ Untuk keadaan darurat, segera hubungi pihak berwenang setempat")
st.caption(f"🔄 Cache: 10 menit | Historis: {len(st.session_state.historical_data)} data points")

# Sidebar
st.sidebar.title("⚙️ Pengaturan & Info")

st.sidebar.subheader("📱 Telegram Bot")
if TELEGRAM_ENABLED:
    subscriber_data = load_subscribers()
    total_subs = len(subscriber_data.get('subscribers', []))
    
    st.sidebar.success("✅ Bot Aktif")
    st.sidebar.info(f"""
**Status:**
- Token: {'✓ Terisi' if TELEGRAM_BOT_TOKEN else '✗ Kosong'}
- Subscribers: {total_subs} user
- Notifikasi: Otomatis saat status berubah

**Mode:**
Auto-registration dengan /start command

**Log Terakhir:**
{len(st.session_state.telegram_log)} pesan
""")
else:
    st.sidebar.warning("⚠️ Bot Tidak Aktif")
    st.sidebar.caption("Isi konfigurasi di kode untuk mengaktifkan")

st.sidebar.divider()

st.sidebar.subheader("📍 Lokasi Monitoring")
st.sidebar.info(f"""
**Desa Petir, Kec. Dramaga**
Kabupaten Bogor, Jawa Barat

**Koordinat:**
- Latitude: {LOCATION_LAT:.6f}°S
- Longitude: {LOCATION_LON:.6f}°E

**Kode Wilayah:**
- ADM4: {KODE_WILAYAH_ADM4}
- Format: Prov.Kab.Kec.Desa

**Sumber Data:**
- BMKG API Publik
- Update: Setiap 3 jam
- Format: JSON Real-time
""")

st.sidebar.divider()

st.sidebar.subheader("ℹ️ Tentang Dashboard")
st.sidebar.info("""
Dashboard Early Warning System untuk monitoring risiko longsor dengan data real-time dari BMKG API Publik.

**Parameter Monitoring:**
- 🌧️ Curah hujan (mm/jam)
- 💧 Kelembaban udara (%)
- 🌡️ Suhu udara (°C)
- 💨 Kecepatan & arah angin
- 📊 Kondisi cuaca

**Tingkat Bahaya:**
- 🟢 Aman: Hujan < 20mm/jam
- 🟡 Waspada: Hujan 20-50mm/jam
- 🔴 Bahaya: Hujan > 50mm/jam + RH > 85%

**Standar:** BNPB & BMKG

**Telegram Auto-Registration:**
User cukup /start di bot untuk mendaftar otomatis!
""")

st.sidebar.divider()

st.sidebar.subheader("📊 Statistik Sistem")
if len(st.session_state.historical_data) > 0:
    df_stats = pd.DataFrame(st.session_state.historical_data)
    st.sidebar.metric("Total Data Points", len(df_stats))
    st.sidebar.metric("Rata-rata Curah Hujan", f"{df_stats['curah_hujan'].mean():.1f} mm/jam")
    st.sidebar.metric("Rata-rata Kelembaban", f"{df_stats['kelembaban'].mean():.1f}%")
    st.sidebar.metric("Notifikasi Aktif", len(st.session_state.notifications))

st.sidebar.divider()

st.sidebar.subheader("🔔 Pengaturan Notifikasi")
enable_sound = st.sidebar.checkbox("Aktifkan Suara Notifikasi", value=True)
enable_popup = st.sidebar.checkbox("Aktifkan Pop-up Alert", value=True)
enable_telegram_auto = st.sidebar.checkbox("Telegram Auto-send", value=TELEGRAM_ENABLED)

if st.sidebar.button("🗑️ Hapus Data Historis"):
    st.session_state.historical_data = []
    st.session_state.notifications = []
    st.session_state.telegram_log = []
    st.sidebar.success("Data berhasil dihapus!")
    time.sleep(1)
    st.rerun()

st.sidebar.divider()

# Informasi tambahan untuk Bot Listener
st.sidebar.subheader("🤖 Bot Listener Status")
if os.path.exists(SUBSCRIBERS_FILE):
    file_time = datetime.fromtimestamp(os.path.getmtime(SUBSCRIBERS_FILE))
    st.sidebar.success(f"✅ File ditemukan\n\nUpdate: {file_time.strftime('%H:%M:%S')}")
else:
    st.sidebar.warning("⚠️ File subscribers belum ada\n\nJalankan bot listener terlebih dahulu")

st.sidebar.divider()
st.sidebar.caption("📄 Data BMKG diperbarui setiap 3 jam")
st.sidebar.caption("💾 Cache lokal: 10 menit")
st.sidebar.caption("📡 API: api.bmkg.go.id/publik")
st.sidebar.caption("🤖 Auto-registration: Aktif")

st.sidebar.caption("v4.0 - Dashboard EWS + Auto Telegram Bot")
