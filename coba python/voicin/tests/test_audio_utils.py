import os
import sqlite3
import tempfile
import unittest

import app as app_module
from app import get_audio_extension


class AudioExtensionTests(unittest.TestCase):
    def test_webm_recording_extension_is_supported(self):
        self.assertEqual(get_audio_extension('recording.webm', 'audio/webm'), '.webm')

    def test_unsupported_extension_is_rejected(self):
        self.assertIsNone(get_audio_extension('recording.exe', 'application/x-msdownload'))


class HistorySchemaTests(unittest.TestCase):
    def test_init_db_adds_missing_kategori_column(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            conn = sqlite3.connect(db_path)
            conn.execute(
                'CREATE TABLE history (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL, tanggal TEXT NOT NULL, hasil TEXT NOT NULL, confidence REAL NOT NULL)'
            )
            conn.commit()
            conn.close()

            original_db = app_module.DATABASE
            app_module.DATABASE = db_path
            try:
                app_module.init_db()
                conn = sqlite3.connect(db_path)
                columns = [row[1] for row in conn.execute('PRAGMA table_info(history)')]
                conn.close()
                self.assertIn('kategori', columns)
            finally:
                app_module.DATABASE = original_db


if __name__ == '__main__':
    unittest.main()
