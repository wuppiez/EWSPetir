"""
Telegram Bot Listener - Auto Registration System (FIXED)
Script ini harus dijalankan secara terpisah dan terus menerus (24/7)
untuk mendengarkan command /start dan /stop dari user

Cara menjalankan:
1. Install: pip install python-telegram-bot
2. Jalankan: python telegram_bot_listener.py
3. Biarkan script ini running di background

Command yang tersedia:
- /start - Registrasi untuk menerima notifikasi
- /stop - Berhenti menerima notifikasi
- /status - Cek status registrasi
- /info - Info tentang sistem EWS
"""

import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==================== KONFIGURASI ====================
TELEGRAM_BOT_TOKEN = "8271915231:AAGyCe7dKqbZMmrAs4_XHlfes-JaHNPJTeE"
SUBSCRIBERS_FILE = "telegram_subscribers.json"
# ====================================================

def load_subscribers():
    """Load daftar subscriber dari file JSON"""
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"subscribers": [], "metadata": {}}
    return {"subscribers": [], "metadata": {}}

def save_subscribers(data):
    """Simpan daftar subscriber ke file JSON"""
    try:
        with open(SUBSCRIBERS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving subscribers: {e}")
        return False

def add_subscriber(chat_id, username=None, first_name=None):
    """Tambah subscriber baru"""
    data = load_subscribers()
    
    # Cek apakah sudah terdaftar
    for sub in data["subscribers"]:
        if sub["chat_id"] == str(chat_id):
            # Update info jika sudah ada
            sub["username"] = username
            sub["first_name"] = first_name
            sub["last_updated"] = datetime.now().isoformat()
            save_subscribers(data)
            return False  # Sudah terdaftar sebelumnya
    
    # Tambah subscriber baru
    data["subscribers"].append({
        "chat_id": str(chat_id),
        "username": username,
        "first_name": first_name,
        "registered_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "active": True
    })
    
    data["metadata"]["total_subscribers"] = len(data["subscribers"])
    data["metadata"]["last_update"] = datetime.now().isoformat()
    
    save_subscribers(data)
    return True  # Berhasil ditambahkan

def remove_subscriber(chat_id):
    """Hapus subscriber"""
    data = load_subscribers()
    
    original_count = len(data["subscribers"])
    data["subscribers"] = [
        sub for sub in data["subscribers"] 
        if sub["chat_id"] != str(chat_id)
    ]
    
    if len(data["subscribers"]) < original_count:
        data["metadata"]["total_subscribers"] = len(data["subscribers"])
        data["metadata"]["last_update"] = datetime.now().isoformat()
        save_subscribers(data)
        return True
    
    return False

def is_subscriber(chat_id):
    """Cek apakah user sudah terdaftar"""
    data = load_subscribers()
    for sub in data["subscribers"]:
        if sub["chat_id"] == str(chat_id) and sub.get("active", True):
            return True
    return False

# ==================== COMMAND HANDLERS ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /start command"""
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    is_new = add_subscriber(chat_id, username, first_name)
    
    if is_new:
        welcome_message = f"""
✅ <b>Registrasi Berhasil!</b>

Halo {first_name}! 👋

Anda telah terdaftar untuk menerima notifikasi dari:
<b>🚨 Early Warning System Longsor</b>
<b>📍 Desa Petir, Dramaga, Bogor</b>

<b>Anda akan menerima:</b>
• 🔴 Alert BAHAYA - Saat risiko tinggi
• 🟡 Alert WASPADA - Saat risiko sedang
• 📊 Laporan berkala kondisi cuaca
• ⚠️ Rekomendasi tindakan darurat

<b>Command yang tersedia:</b>
/status - Cek status registrasi
/info - Info tentang sistem EWS
/stop - Berhenti menerima notifikasi

<b>Chat ID Anda:</b> <code>{chat_id}</code>

Tetap waspada dan selalu siaga! 🙏
"""
    else:
        welcome_message = f"""
ℹ️ <b>Sudah Terdaftar</b>

Halo {first_name}! 👋

Anda sudah terdaftar sebelumnya untuk menerima notifikasi dari sistem EWS Longsor Desa Petir.

<b>Status:</b> ✅ Aktif
<b>Chat ID:</b> <code>{chat_id}</code>

Gunakan /status untuk cek info lengkap.
"""
    
    await update.message.reply_text(welcome_message, parse_mode='HTML')
    
    # Log ke console
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
          f"{'NEW' if is_new else 'EXISTING'} subscriber: {chat_id} (@{username})")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /stop command"""
    chat_id = update.effective_chat.id
    
    removed = remove_subscriber(chat_id)
    
    if removed:
        message = """
✅ <b>Unsubscribe Berhasil</b>

Anda telah berhenti menerima notifikasi dari sistem EWS Longsor.

Jika ingin berlangganan lagi, gunakan command:
/start

Terima kasih telah menggunakan layanan kami! 🙏
"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"UNSUBSCRIBED: {chat_id}")
    else:
        message = """
ℹ️ <b>Info</b>

Anda belum terdaftar sebagai subscriber.

Untuk mendaftar, gunakan command:
/start
"""
    
    await update.message.reply_text(message, parse_mode='HTML')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /status command"""
    chat_id = update.effective_chat.id
    
    if is_subscriber(chat_id):
        data = load_subscribers()
        
        # Cari info subscriber
        subscriber_info = None
        for sub in data["subscribers"]:
            if sub["chat_id"] == str(chat_id):
                subscriber_info = sub
                break
        
        if subscriber_info:
            reg_date = datetime.fromisoformat(subscriber_info["registered_at"])
            
            message = f"""
📊 <b>Status Registrasi</b>

✅ Status: <b>AKTIF</b>
👤 Nama: {subscriber_info.get('first_name', 'N/A')}
🆔 Username: @{subscriber_info.get('username', 'N/A')}
💬 Chat ID: <code>{chat_id}</code>

📅 Terdaftar sejak:
{reg_date.strftime('%d %B %Y, %H:%M WIB')}

📊 Total Subscriber: {data['metadata'].get('total_subscribers', 0)} orang

<b>Layanan yang aktif:</b>
• 🔴 Alert BAHAYA
• 🟡 Alert WASPADA
• 📊 Laporan berkala
• ✅ Info status AMAN

Gunakan /stop untuk berhenti berlangganan.
"""
        else:
            message = "❌ Data tidak ditemukan. Silakan /start ulang."
    else:
        message = """
❌ <b>Belum Terdaftar</b>

Anda belum terdaftar sebagai subscriber.

Untuk mendaftar dan menerima notifikasi, gunakan:
/start
"""
    
    await update.message.reply_text(message, parse_mode='HTML')

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /info command"""
    message = """
ℹ️ <b>Info Sistem EWS Longsor</b>

<b>🚨 Early Warning System</b>
Sistem peringatan dini untuk monitoring risiko longsor dengan data real-time dari BMKG.

<b>📍 Lokasi Monitoring:</b>
Desa Petir, Kecamatan Dramaga
Kabupaten Bogor, Jawa Barat

<b>📊 Parameter yang Dimonitor:</b>
• 🌧️ Curah hujan (mm/jam)
• 💧 Kelembaban udara (%)
• 🌡️ Suhu udara (°C)
• 💨 Kecepatan & arah angin
• ☁️ Kondisi cuaca

<b>🚦 Tingkat Bahaya:</b>
🟢 AMAN: Hujan < 20mm/jam
🟡 WASPADA: Hujan 20-50mm/jam
🔴 BAHAYA: Hujan > 50mm/jam + RH > 85%

<b>📱 Notifikasi yang Dikirim:</b>
• Alert otomatis saat status berubah
• Rekomendasi tindakan darurat
• Laporan kondisi cuaca berkala

<b>📞 Kontak Darurat:</b>
• BPBD Kab. Bogor: (0251) 8324000
• SAR Nasional: 115
• Ambulans: 118 / 119

<b>🔗 Sumber Data:</b>
BMKG API Publik (api.bmkg.go.id)

<b>Command Bot:</b>
/start - Daftar notifikasi
/stop - Berhenti notifikasi
/status - Cek status
/info - Info sistem

Tetap waspada dan selalu siaga! 🙏
"""
    
    await update.message.reply_text(message, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /help command"""
    message = """
📖 <b>Panduan Penggunaan Bot</b>

<b>Command yang Tersedia:</b>

/start - Daftar untuk menerima notifikasi
/stop - Berhenti menerima notifikasi
/status - Cek status registrasi Anda
/info - Info tentang sistem EWS
/help - Tampilkan panduan ini

<b>Cara Menggunakan:</b>

1️⃣ Ketik /start untuk mendaftar
2️⃣ Anda akan otomatis menerima notifikasi
3️⃣ Gunakan /status untuk cek registrasi
4️⃣ Ketik /stop jika ingin berhenti

<b>Notifikasi Otomatis:</b>
Bot akan mengirim alert secara otomatis ketika:
• Status berubah ke BAHAYA 🔴
• Status berubah ke WASPADA 🟡
• Status kembali AMAN 🟢
• Laporan berkala (opsional)

Butuh bantuan? Hubungi admin sistem.
"""
    
    await update.message.reply_text(message, parse_mode='HTML')

# ==================== MAIN FUNCTION ====================

def main():
    """Main function untuk menjalankan bot"""
    
    print("="*60)
    print("🤖 TELEGRAM BOT LISTENER - EWS LONGSOR")
    print("📍 Desa Petir, Dramaga, Bogor")
    print("="*60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Subscribers file: {SUBSCRIBERS_FILE}")
    print("🔄 Bot is running... (Press Ctrl+C to stop)")
    print("="*60)
    
    # Load existing subscribers
    data = load_subscribers()
    print(f"📊 Current subscribers: {len(data.get('subscribers', []))} users")
    print()
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Start the bot
    print("✅ Bot handlers registered")
    print("🎯 Waiting for commands...")
    print()
    
    # Run polling - ini yang diperbaiki
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        print("="*60)
        print("⏹️  Bot stopped by user")
        print(f"⏰ Stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        data = load_subscribers()
        print(f"📊 Final subscribers: {len(data.get('subscribers', []))} users")
        print("="*60)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()