from flask import Flask, request, jsonify, render_template_string, send_from_directory
import os
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'zip'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Upload ZIP</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; }
        .upload-box { border: 2px dashed #ccc; padding: 30px; text-align: center; border-radius: 10px; }
        .upload-box:hover { border-color: #007bff; }
        input[type="file"] { margin: 20px 0; }
        button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .message { margin-top: 20px; padding: 10px; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .file-list { margin-top: 30px; }
        .file-item { padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
        .file-item a { color: #007bff; text-decoration: none; }
        .file-item a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Upload ZIP</h1>
    <div class="upload-box">
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".zip" required>
            <br>
            <button type="submit">Upload</button>
        </form>
    </div>
    <div id="message" class="message" style="display: none;"></div>
    
    <div class="file-list">
        <h2>Ficheiros</h2>
        <div id="files"></div>
    </div>
    
    <script>
        const form = document.querySelector('form');
        const messageDiv = document.getElementById('message');
        const filesDiv = document.getElementById('files');
        
        async function loadFiles() {
            const response = await fetch('/uploads');
            const data = await response.json();
            filesDiv.innerHTML = data.files.map(f => 
                `<div class="file-item">
                    <span>${f}</span>
                    <a href="/download/${f}">Download</a>
                </div>`
            ).join('') || '<p>Nenhum ficheiro.</p>';
        }
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            messageDiv.style.display = 'block';
            messageDiv.className = 'message ' + (result.success ? 'success' : 'error');
            messageDiv.textContent = result.message;
            
            if (result.success) {
                loadFiles();
            }
        });
        
        loadFiles();
    </script>
</body>
</html>
    ''')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum ficheiro enviado'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Nenhum ficheiro selecionado'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Apenas ficheiros ZIP são permitidos'}), 400
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    file.save(filepath)
    
    return jsonify({
        'success': True,
        'message': f'Ficheiro {filename} enviado com sucesso!'
    })


@app.route('/uploads')
def list_uploads():
    files = os.listdir(UPLOAD_FOLDER)
    return jsonify({'files': files})


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
