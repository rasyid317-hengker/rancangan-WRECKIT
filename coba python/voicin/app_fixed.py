from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename

from model import predict_voice

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DATABASE = os.path.join(BASE_DIR, 'database.db')
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'webm', 'm4a', 'ogg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
for folder in ['temp', 'original', 'ai']:
    os.makedirs(os.path.join(UPLOAD_FOLDER, folder), exist_ok=True)


def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history'")
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        cursor.execute('''
            CREATE TABLE history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                tanggal TEXT NOT NULL,
                hasil TEXT NOT NULL,
                confidence REAL NOT NULL,
                kategori TEXT NOT NULL DEFAULT 'unknown'
            )
        ''')
        conn.commit()
        conn.close()
        return

    cursor.execute("PRAGMA table_info(history)")
    columns = {row[1] for row in cursor.fetchall()}
    if 'kategori' not in columns:
        cursor.execute('''
            CREATE TABLE history_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                tanggal TEXT NOT NULL,
                hasil TEXT NOT NULL,
                confidence REAL NOT NULL,
                kategori TEXT NOT NULL DEFAULT 'unknown'
            )
        ''')
        cursor.execute('''
            INSERT INTO history_new (id, filename, tanggal, hasil, confidence, kategori)
            SELECT id, filename, tanggal, hasil, confidence, 'unknown'
            FROM history
        ''')
        cursor.execute('DROP TABLE history')
        cursor.execute('ALTER TABLE history_new RENAME TO history')
        conn.commit()

    conn.close()


def simpan_history(filename, hasil, confidence, kategori):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        'INSERT INTO history (filename, tanggal, hasil, confidence, kategori) VALUES (?, ?, ?, ?, ?)',
        (filename, tanggal, hasil, confidence, kategori)
    )
    conn.commit()
    conn.close()


def ambil_semua_history():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT filename, tanggal, hasil, confidence, kategori FROM history ORDER BY id DESC')
    data = cursor.fetchall()
    conn.close()
    return data


def get_audio_extension(filename, content_type=None):
    if not filename:
        return None
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext in ALLOWED_EXTENSIONS:
        return f'.{ext}'
    mime_map = {
        'audio/wav': '.wav',
        'audio/x-wav': '.wav',
        'audio/mpeg': '.mp3',
        'audio/mp3': '.mp3',
        'audio/webm': '.webm',
        'audio/mp4': '.m4a',
        'audio/ogg': '.ogg',
    }
    return mime_map.get(content_type.lower(), None) if content_type else None


def save_temp_audio(file_storage):
    ext = get_audio_extension(file_storage.filename, file_storage.mimetype)
    if not ext:
        return None
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    safe_name = secure_filename(os.path.splitext(file_storage.filename)[0]) or 'audio'
    temp_path = os.path.join(UPLOAD_FOLDER, 'temp', f'{safe_name}_{timestamp}{ext}')
    file_storage.save(temp_path)
    return temp_path


def move_to_category(temp_path, hasil):
    category = 'original' if hasil == 'Original Voice' else 'ai'
    target_folder = os.path.join(UPLOAD_FOLDER, category)
    os.makedirs(target_folder, exist_ok=True)
    target_path = os.path.join(target_folder, os.path.basename(temp_path))
    if os.path.exists(target_path):
        stem, ext = os.path.splitext(target_path)
        target_path = f'{stem}_{datetime.now().strftime("%H%M%S")}{ext}'
    os.replace(temp_path, target_path)
    return target_path


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/history')
def history():
    return render_template('history.html', data=ambil_semua_history())


@app.route('/history/clear', methods=['POST'])
def clear_history():
    conn = sqlite3.connect(DATABASE)
    conn.execute('DELETE FROM history')
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'Tidak ada file audio'}), 400
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'Pilih file audio terlebih dahulu.'}), 400
    try:
        temp_path = save_temp_audio(file)
        if not temp_path:
            return jsonify({'error': 'Format file tidak didukung.'}), 400
        hasil, confidence = predict_voice(temp_path)
        final_path = move_to_category(temp_path, hasil)
        filename = os.path.basename(final_path)
        kategori = 'Original' if hasil == 'Original Voice' else 'AI'
        simpan_history(filename, hasil, confidence, kategori)
        return jsonify({'filename': filename, 'hasil': hasil, 'confidence': confidence, 'kategori': kategori})
    except Exception as exc:
        return jsonify({'error': f'Gagal memproses audio: {exc}'}), 500


@app.route('/record', methods=['POST'])
def record_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'Tidak ada data audio dari browser.'}), 400
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'Rekaman kosong. Tekan Record lagi.'}), 400
    try:
        temp_path = save_temp_audio(file)
        if not temp_path:
            return jsonify({'error': 'Rekaman tidak bisa disimpan.'}), 400
        hasil, confidence = predict_voice(temp_path)
        final_path = move_to_category(temp_path, hasil)
        filename = os.path.basename(final_path)
        kategori = 'Original' if hasil == 'Original Voice' else 'AI'
        simpan_history(filename, hasil, confidence, kategori)
        return jsonify({'filename': filename, 'hasil': hasil, 'confidence': confidence, 'kategori': kategori})
    except Exception as exc:
        return jsonify({'error': f'Gagal memproses rekaman: {exc}'}), 500


init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
