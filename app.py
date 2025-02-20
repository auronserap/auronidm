from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import yt_dlp
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///downloads.db'
db = SQLAlchemy(app)

class Download(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    filename = db.Column(db.String(500))
    format_id = db.Column(db.String(50))
    status = db.Column(db.String(50), default='Bekliyor')
    progress = db.Column(db.Float, default=0)
    file_size = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get-formats', methods=['POST'])
def get_formats():
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({'error': 'URL gerekli'}), 400

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'tr,en-US;q=0.7,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
            },
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'cookiefile': 'cookies.txt',
            'extractor_retries': 3,
            'socket_timeout': 30
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return jsonify({'error': 'Video bilgileri alınamadı'}), 400

            formats = info.get('formats', [])
            if not formats:
                return jsonify({'error': 'Video formatları bulunamadı'}), 400

            available_qualities = {}
            video_formats = [f for f in formats if f.get('vcodec', 'none') != 'none' and 'height' in f]
            audio_formats = [f for f in formats if f.get('acodec', 'none') != 'none' and f.get('vcodec', 'none') == 'none']

            if audio_formats:
                best_audio = max(audio_formats, key=lambda x: x.get('tbr', 0))
                
                for vf in video_formats:
                    height = vf.get('height', 0)
                    if height > 0:
                        format_id = f"{vf['format_id']}+{best_audio['format_id']}"
                        filesize = vf.get('filesize', 0) or vf.get('approximate_filesize', 0)
                        
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
                                'vcodec': vf.get('vcodec', ''),
                                'acodec': best_audio.get('acodec', ''),
                                'ext': vf.get('ext', 'mp4'),
                                'fps': vf.get('fps', 0),
                                'tbr': vf.get('tbr', 0)
                            }

            sorted_qualities = sorted(
                available_qualities.items(),
                key=lambda x: x[1]['height'],
                reverse=True
            )

            formats_list = []
            for quality, data in sorted_qualities:
                filesize_mb = data['filesize'] / 1024 / 1024
                formats_list.append({
                    'quality': quality,
                    'format_id': data['format_id'],
                    'ext': data['ext'],
                    'filesize': f"{filesize_mb:.1f} MB",
                    'vcodec': data['vcodec'],
                    'acodec': data['acodec'],
                    'fps': data['fps'],
                    'tbr': data['tbr']
                })

            return jsonify({
                'formats': formats_list,
                'title': info.get('title', '')
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    try:
        url = request.json.get('url')
        format_id = request.json.get('format_id')
        
        if not url or not format_id:
            return jsonify({'error': 'URL ve format_id gerekli'}), 400

        ydl_opts = {
            'format': format_id,
            'quiet': True,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return jsonify({'error': 'Video bilgileri alınamadı'}), 400

            video_url = info['url']
            filename = f"{info['title']}.{info['ext']}"

            # Video URL'sini ve dosya adını doğrudan kullanıcıya gönder
            return jsonify({
                'download_url': video_url,
                'filename': filename
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)

application = app 