document.addEventListener('DOMContentLoaded', () => {
  const uploadForm = document.getElementById('uploadForm');
  const fileInput = document.getElementById('fileInput');
  const fileName = document.getElementById('fileName');
  const btnUpload = document.getElementById('btnUpload');
  const btnRecord = document.getElementById('btnRecord');
  const btnStop = document.getElementById('btnStop');
  const resultCard = document.getElementById('resultCard');
  const loading = document.getElementById('loading');
  const resultLabel = document.getElementById('resultLabel');
  const confidenceText = document.getElementById('confidenceText');
  const resultIcon = document.getElementById('resultIcon');
  const confidenceBar = document.getElementById('confidenceBar');
  const recordTimer = document.getElementById('recordTimer');
  const clearHistoryBtn = document.getElementById('btnClearHistory');

  let mediaRecorder;
  let chunks = [];
  let stream;
  let recordingTimer;
  let recordingSeconds = 0;

  const statusBox = document.createElement('div');
  statusBox.className = 'status-message';
  statusBox.style.display = 'none';
  if (resultCard) {
    resultCard.parentNode.insertBefore(statusBox, resultCard);
  }

  const showStatus = (message, type = 'info') => {
    if (!statusBox) return;
    statusBox.textContent = message;
    statusBox.className = `status-message ${type}`;
    statusBox.style.display = 'block';
  };

  const hideStatus = () => {
    statusBox.textContent = '';
    statusBox.style.display = 'none';
  };

  const setResult = (hasil, confidence) => {
    if (!resultCard || !resultLabel || !confidenceText || !resultIcon || !confidenceBar) return;
    resultLabel.textContent = hasil;
    confidenceText.textContent = `Confidence: ${confidence}%`;
    resultCard.style.display = 'block';
    resultCard.className = 'result-card';
    resultCard.classList.add(hasil === 'Original Voice' ? 'original' : 'ai');
    resultIcon.className = hasil === 'Original Voice' ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-xmark';
    confidenceBar.style.width = `${confidence}%`;
  };

  const resetResult = () => {
    if (!resultCard || !confidenceBar) return;
    resultCard.style.display = 'none';
    resultCard.className = 'result-card';
    confidenceBar.style.width = '0%';
  };

  const startTimer = () => {
    recordingSeconds = 0;
    recordTimer.textContent = '00:00';
    clearInterval(recordingTimer);
    recordingTimer = setInterval(() => {
      recordingSeconds += 1;
      const mins = String(Math.floor(recordingSeconds / 60)).padStart(2, '0');
      const secs = String(recordingSeconds % 60).padStart(2, '0');
      recordTimer.textContent = `${mins}:${secs}`;
    }, 1000);
  };

  const stopTimer = () => {
    clearInterval(recordingTimer);
    recordTimer.textContent = '00:00';
  };

  if (fileInput && fileName && btnUpload) {
    fileInput.addEventListener('change', () => {
      const file = fileInput.files[0];
      if (file) {
        fileName.textContent = file.name;
        btnUpload.disabled = false;
        hideStatus();
      } else {
        fileName.textContent = '';
        btnUpload.disabled = true;
      }
    });
  }

  if (uploadForm && fileInput && btnUpload) {
    uploadForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const file = fileInput.files[0];
      if (!file) {
        showStatus('Pilih file audio terlebih dahulu.', 'error');
        return;
      }

      const formData = new FormData();
      formData.append('audio', file);
      if (loading) loading.style.display = 'block';
      hideStatus();
      resetResult();

      try {
        const response = await fetch('/upload', { method: 'POST', body: formData });
        const data = await response.json();
        if (loading) loading.style.display = 'none';
        if (response.ok) {
          setResult(data.hasil, data.confidence);
          showStatus('Analisis selesai.', 'success');
        } else {
          showStatus(data.error || 'Gagal menganalisis audio.', 'error');
        }
      } catch (error) {
        if (loading) loading.style.display = 'none';
        showStatus('Gagal mengirim file. Periksa koneksi dan format file.', 'error');
      }
    });
  }

  if (btnRecord && btnStop) {
    btnRecord.addEventListener('click', async () => {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showStatus('Browser Anda tidak mendukung akses mikrofon.', 'error');
        return;
      }

      try {
        showStatus('Meminta izin mikrofon...', 'info');
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '';
        mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
        chunks = [];
        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) chunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
          const blob = new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' });
          chunks = [];
          const formData = new FormData();
          formData.append('audio', blob, 'recording.webm');
          if (loading) loading.style.display = 'block';
          hideStatus();
          resetResult();

          try {
            const response = await fetch('/record', { method: 'POST', body: formData });
            const data = await response.json();
            if (loading) loading.style.display = 'none';
            if (response.ok) {
              setResult(data.hasil, data.confidence);
              showStatus('Rekaman berhasil dianalisis.', 'success');
            } else {
              showStatus(data.error || 'Gagal menganalisis rekaman.', 'error');
            }
          } catch (error) {
            if (loading) loading.style.display = 'none';
            showStatus('Gagal mengirim rekaman. Coba lagi.', 'error');
          }

          stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        startTimer();
        btnRecord.disabled = true;
        btnStop.disabled = false;
        showStatus('Rekaman sedang berjalan...', 'info');
      } catch (err) {
        showStatus('Tidak bisa mengakses mikrofon. Izinkan akses mikrofon lalu coba lagi.', 'error');
      }
    });

    btnStop.addEventListener('click', () => {
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        stopTimer();
        btnRecord.disabled = false;
        btnStop.disabled = true;
      }
    });
  }

  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener('click', async () => {
      if (!confirm('Hapus semua riwayat deteksi?')) return;
      const response = await fetch('/history/clear', { method: 'POST' });
      if (response.ok) {
        window.location.reload();
      }
    });
  }
});
