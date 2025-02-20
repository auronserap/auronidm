import os
import sys
import json
import time
import requests
from datetime import datetime
from tqdm import tqdm
import yt_dlp
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLineEdit, QLabel, 
                           QProgressBar, QFileDialog, QTableWidget, 
                           QTableWidgetItem, QComboBox, QTabWidget,
                           QDateTimeEdit, QMessageBox, QDialog, QDialogButtonBox,
                           QStatusBar, QHeaderView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDateTime, QTimer
from PyQt5.QtGui import QIcon

class VideoQualityDialog(QDialog):
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.selected_format = None
        self.formats = []
        self.initUI()
        self.load_formats()
        
    def initUI(self):
        self.setWindowTitle("Video Kalitesi Seçimi")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Kalite seçimi
        self.quality_combo = QComboBox()
        layout.addWidget(QLabel("Kalite Seçin:"))
        layout.addWidget(self.quality_combo)
        
        # Bilgi etiketi
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # Butonlar
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def load_formats(self):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                if not info:
                    raise Exception("Video bilgileri alınamadı")
                    
                formats = info.get('formats', [])
                if not formats:
                    raise Exception("Video formatları bulunamadı")
                    
                print("\nTüm formatlar:")
                available_qualities = {}
                
                # Önce video formatlarını kontrol et
                video_formats = [f for f in formats if f.get('vcodec', 'none') != 'none' and 'height' in f]
                audio_formats = [f for f in formats if f.get('acodec', 'none') != 'none' and f.get('vcodec', 'none') == 'none']
                
                if audio_formats:  # En iyi ses formatını seç
                    best_audio = max(audio_formats, key=lambda x: x.get('tbr', 0))
                    
                    for vf in video_formats:
                        try:
                            height = vf.get('height', 0)
                            if height > 0:
                                format_id = f"{vf['format_id']}+{best_audio['format_id']}"
                                filesize = vf.get('filesize', 0) or vf.get('approximate_filesize', 0)
                                
                                # Kalite anahtarını belirle
                                quality_key = f"{height}p"
                                if height == 1440:
                                    quality_key = "2K"
                                elif height == 2160:
                                    quality_key = "4K"
                                
                                # Format bilgilerini yazdır
                                print(f"Format ID: {format_id}, Çözünürlük: {height}p, "
                                      f"Video Codec: {vf.get('vcodec', 'N/A')}, "
                                      f"Ses Codec: {best_audio.get('acodec', 'N/A')}, "
                                      f"Boyut: {filesize/1024/1024:.1f}MB")
                                
                                if quality_key not in available_qualities or filesize > available_qualities[quality_key]['filesize']:
                                    available_qualities[quality_key] = {
                                        'format_id': format_id,
                                        'filesize': filesize,
                                        'height': height,
                                        'vcodec': vf.get('vcodec', ''),
                                        'acodec': best_audio.get('acodec', ''),
                                        'ext': vf.get('ext', 'mp4'),
                                        'fps': vf.get('fps', 0),
                                        'tbr': vf.get('tbr', 0)
                                    }
                        except Exception as format_error:
                            print(f"Format işleme hatası: {format_error}")
                            continue
                
                if not available_qualities:
                    # Birleşik formatları kontrol et
                    for f in formats:
                        try:
                            if (f.get('acodec', 'none') != 'none' and 
                                f.get('vcodec', 'none') != 'none' and 
                                'height' in f):
                                
                                height = f.get('height', 0)
                                if height > 0:
                                    format_id = f.get('format_id')
                                    filesize = f.get('filesize', 0) or f.get('approximate_filesize', 0)
                                    
                                    quality_key = f"{height}p"
                                    if height == 1440:
                                        quality_key = "2K"
                                    elif height == 2160:
                                        quality_key = "4K"
                                    
                                    if quality_key not in available_qualities or filesize > available_qualities[quality_key]['filesize']:
                                        available_qualities[quality_key] = {
                                            'format_id': format_id,
                                            'filesize': filesize,
                                            'height': height,
                                            'vcodec': f.get('vcodec', ''),
                                            'acodec': f.get('acodec', ''),
                                            'ext': f.get('ext', 'mp4'),
                                            'fps': f.get('fps', 0),
                                            'tbr': f.get('tbr', 0)
                                        }
                        except Exception as format_error:
                            print(f"Format işleme hatası: {format_error}")
                            continue
                
                if not available_qualities:
                    raise Exception("Uygun video formatı bulunamadı")
                
                print("\nSeçilen formatlar:")
                # Kaliteleri yüksekten düşüğe sırala
                quality_order = {
                    "4K": 2160,
                    "2K": 1440,
                    "1080p": 1080,
                    "720p": 720,
                    "480p": 480,
                    "360p": 360,
                    "240p": 240,
                    "144p": 144
                }
                
                sorted_qualities = sorted(
                    available_qualities.items(),
                    key=lambda x: quality_order.get(x[0], x[1]['height']),
                    reverse=True
                )
                
                # Combo box'ı temizle
                self.quality_combo.clear()
                
                # Format listesini güncelle
                self.formats = []
                
                for quality, data in sorted_qualities:
                    try:
                        filesize_mb = data['filesize'] / 1024 / 1024
                        format_text = f"{quality} ({data['ext']}) - {filesize_mb:.1f} MB"
                        
                        # Format bilgilerini listeye ekle
                        self.formats.append(data)
                        self.quality_combo.addItem(format_text, data['format_id'])
                        
                        print(f"Eklenen format: {format_text} - Format ID: {data['format_id']} - "
                              f"Video: {data['vcodec']}, Ses: {data['acodec']}")
                              
                    except Exception as add_error:
                        print(f"Format ekleme hatası: {add_error}")
                        continue
                
                # İlk kaliteyi seç ve bilgileri güncelle
                if self.quality_combo.count() > 0:
                    self.quality_combo.setCurrentIndex(0)
                    self.update_info(0)
                    
                self.quality_combo.currentIndexChanged.connect(self.update_info)
                
        except Exception as e:
            error_msg = str(e)
            print(f"Format yükleme hatası: {error_msg}")
            self.info_label.setText(f"Hata: {error_msg}")
            self.quality_combo.setEnabled(False)
            
    def update_info(self, index):
        try:
            if 0 <= index < len(self.formats):
                data = self.formats[index]
                
                info = []
                info.append(f"Video Codec: {data['vcodec']}")
                info.append(f"Ses Codec: {data['acodec']}")
                
                if data['fps']:
                    info.append(f"FPS: {data['fps']}")
                if data['tbr']:
                    info.append(f"Bit Hızı: {data['tbr']:.1f}kbps")
                    
                self.info_label.setText("\n".join(info))
                
        except Exception as e:
            print(f"Bilgi güncelleme hatası: {str(e)}")
            
    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
        
    def get_selected_format(self):
        try:
            index = self.quality_combo.currentIndex()
            if index >= 0:
                return self.quality_combo.itemData(index)
            return None
        except Exception as e:
            print(f"Format seçim hatası: {str(e)}")
            return None

class DownloadThread(QThread):
    progress_updated = pyqtSignal(float)
    download_finished = pyqtSignal()
    download_error = pyqtSignal(str)
    info_updated = pyqtSignal(str, str)  # dosya adı, boyut
    
    def __init__(self, url, format_id=None):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self._is_running = True
        
    def run(self):
        try:
            ydl_opts = {
                'format': self.format_id if self.format_id else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'progress_hooks': [self._progress_hook],
                'quiet': True,
                'no_warnings': True,
                'outtmpl': '%(title)s.%(ext)s'  # Dosya adı şablonu
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Önce video bilgilerini al
                info = ydl.extract_info(self.url, download=False)
                if info:
                    # Dosya adını ve boyutunu hazırla
                    filename = f"{info.get('title', 'video')}.{info.get('ext', 'mp4')}"
                    filesize = info.get('filesize', 0) or info.get('filesize_approx', 0)
                    if filesize:
                        size_str = self.format_size(filesize)
                    else:
                        size_str = "Bilinmiyor"
                        
                    # Bilgileri gönder
                    self.info_updated.emit(filename, size_str)
                    
                    # İndirmeyi başlat
                    ydl.download([self.url])
                    
                if self._is_running:
                    self.download_finished.emit()
                    
        except Exception as e:
            if self._is_running:
                self.download_error.emit(str(e))
                
    def _progress_hook(self, d):
        if not self._is_running:
            raise Exception("İndirme iptal edildi")
            
        if d['status'] == 'downloading':
            try:
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                
                if total > 0:
                    progress = (downloaded / total) * 100
                    self.progress_updated.emit(progress)
                    
            except Exception as e:
                print(f"İlerleme hesaplama hatası: {str(e)}")
                
    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
                
    def terminate(self):
        self._is_running = False
        super().terminate()

class DownloadManager(QMainWindow):
    def __init__(self):
        try:
            super().__init__()
            self.setWindowTitle("İndirme Yöneticisi")
            self.resize(800, 600)
            
            # Ana widget ve layout
            self.central_widget = QWidget()
            self.setCentralWidget(self.central_widget)
            self.layout = QVBoxLayout(self.central_widget)
            
            # URL girişi
            self.url_layout = QHBoxLayout()
            self.url_input = QLineEdit()
            self.url_input.setPlaceholderText("Video URL'sini yapıştırın")
            self.url_layout.addWidget(self.url_input)
            
            self.download_button = QPushButton("İndir")
            self.download_button.clicked.connect(self.start_download)
            self.url_layout.addWidget(self.download_button)
            
            self.layout.addLayout(self.url_layout)
            
            # İndirme listesi
            self.download_list = QTableWidget()
            self.download_list.setColumnCount(4)
            self.download_list.setHorizontalHeaderLabels(["Dosya Adı", "Boyut", "İlerleme", "Durum"])
            self.download_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.layout.addWidget(self.download_list)
            
            # Durum çubuğu
            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)
            
            self.downloads = []
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_progress)
            self.timer.start(1000)
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Program başlatılırken hata oluştu: {str(e)}")
            
    def start_download(self):
        try:
            url = self.url_input.text().strip()
            if not url:
                QMessageBox.warning(self, "Uyarı", "Lütfen bir URL girin")
                return
                
            dialog = VideoQualityDialog(url, self)
            if dialog.exec_() == QDialog.Accepted:
                selected_format = dialog.get_selected_format()
                if selected_format:
                    row = self.download_list.rowCount()
                    self.download_list.insertRow(row)
                    
                    # Başlangıç durumunu ayarla
                    self.download_list.setItem(row, 0, QTableWidgetItem("Hazırlanıyor..."))
                    self.download_list.setItem(row, 1, QTableWidgetItem("-"))
                    self.download_list.setItem(row, 2, QTableWidgetItem("0%"))
                    self.download_list.setItem(row, 3, QTableWidgetItem("Başlatılıyor"))
                    
                    thread = DownloadThread(url, selected_format)
                    thread.progress_updated.connect(lambda p, r=row: self.update_download_progress(r, p))
                    thread.download_finished.connect(lambda r=row: self.download_finished(r))
                    thread.download_error.connect(lambda e, r=row: self.download_error(r, e))
                    thread.info_updated.connect(lambda name, size, r=row: self.update_download_info(r, name, size))
                    
                    self.downloads.append(thread)
                    thread.start()
                    
                    self.status_bar.showMessage(f"İndirme başlatıldı: {url}")
                else:
                    QMessageBox.warning(self, "Uyarı", "Format seçilemedi")
                    
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İndirme başlatılırken hata oluştu: {str(e)}")
            
    def update_download_info(self, row, filename, filesize):
        try:
            if 0 <= row < self.download_list.rowCount():
                self.download_list.setItem(row, 0, QTableWidgetItem(filename))
                self.download_list.setItem(row, 1, QTableWidgetItem(filesize))
                
        except Exception as e:
            print(f"Bilgi güncelleme hatası: {str(e)}")
            
    def update_download_progress(self, row, progress):
        try:
            if 0 <= row < self.download_list.rowCount():
                progress_item = self.download_list.item(row, 2)
                if not progress_item:
                    progress_item = QTableWidgetItem()
                    self.download_list.setItem(row, 2, progress_item)
                progress_item.setText(f"%{progress:.1f}")
                
        except Exception as e:
            print(f"İlerleme güncellenirken hata: {str(e)}")
            
    def download_finished(self, row):
        try:
            if 0 <= row < self.download_list.rowCount():
                status_item = self.download_list.item(row, 3)
                if not status_item:
                    status_item = QTableWidgetItem()
                    self.download_list.setItem(row, 3, status_item)
                status_item.setText("Tamamlandı")
                
                self.status_bar.showMessage("İndirme tamamlandı", 5000)
                
        except Exception as e:
            print(f"İndirme tamamlanırken hata: {str(e)}")
            
    def download_error(self, row, error):
        try:
            if 0 <= row < self.download_list.rowCount():
                status_item = self.download_list.item(row, 3)
                if not status_item:
                    status_item = QTableWidgetItem()
                    self.download_list.setItem(row, 3, status_item)
                status_item.setText(f"Hata: {str(error)}")
                
                self.status_bar.showMessage(f"İndirme hatası: {str(error)}", 5000)
                
        except Exception as e:
            print(f"Hata işlenirken hata: {str(e)}")
            
    def update_progress(self):
        try:
            active_downloads = [d for d in self.downloads if d.isRunning()]
            if active_downloads:
                self.status_bar.showMessage(f"Aktif indirme sayısı: {len(active_downloads)}")
            else:
                self.status_bar.showMessage("İndirme yok")
                
        except Exception as e:
            print(f"İlerleme güncellenirken hata: {str(e)}")
            
    def closeEvent(self, event):
        try:
            active_downloads = [d for d in self.downloads if d.isRunning()]
            if active_downloads:
                reply = QMessageBox.question(
                    self,
                    "Onay",
                    "Aktif indirmeler var. Çıkmak istediğinizden emin misiniz?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    for download in active_downloads:
                        download.terminate()
                    event.accept()
                else:
                    event.ignore()
            else:
                event.accept()
                
        except Exception as e:
            print(f"Program kapatılırken hata: {str(e)}")
            event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DownloadManager()
    window.show()
    sys.exit(app.exec_()) 