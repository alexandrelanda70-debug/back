from flask import Flask, request, jsonify, render_template_string, send_from_directory
import os, uuid
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
CHUNK_FOLDER = 'chunks'
ALLOWED_EXTENSIONS = {'zip'}
CHUNK_SIZE = 2 * 1024 * 1024  # 2 MB por chunk

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CHUNK_FOLDER, exist_ok=True)


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
        .file-item a { color: #007bff; text-decoration: none; margin-right: 10px; }
        .file-item a:hover { text-decoration: underline; }
        .delete-btn { background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; }
        .delete-btn:hover { background: #c82333; }
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
        const CHUNK_SIZE = 2 * 1024 * 1024; // 2 MB
        
        async function loadFiles() {
            const response = await fetch('/uploads');
            const data = await response.json();
            filesDiv.innerHTML = data.files.map(f => 
                `<div class="file-item">
                    <span>${f}</span>
                    <div>
                        <a href="/download/${f}">Download</a>
                        <button class="delete-btn" onclick="deleteFile('${f}')">Eliminar</button>
                    </div>
                </div>`
            ).join('') || '<p>Nenhum ficheiro.</p>';
        }
        
        async function deleteFile(filename) {
            if (!confirm('Tem a certeza que deseja eliminar este ficheiro?')) return;
            
            const response = await fetch(`/delete/${filename}`, { method: 'DELETE' });
            const result = await response.json();
            
            messageDiv.style.display = 'block';
            messageDiv.className = 'message ' + (result.success ? 'success' : 'error');
            messageDiv.textContent = result.message;
            
            if (result.success) {
                loadFiles();
            }
        }
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = form.querySelector('input[type="file"]');
            const file = fileInput.files[0];
            if (!file) return;
            
            const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
            const uploadId = crypto.randomUUID();
            
            messageDiv.style.display = 'block';
            messageDiv.className = 'message success';
            messageDiv.textContent = `A enviar... 0%`;
            
            for (let i = 0; i < totalChunks; i++) {
                const start = i * CHUNK_SIZE;
                const end = Math.min(start + CHUNK_SIZE, file.size);
                const chunk = file.slice(start, end);
                
                const formData = new FormData();
                formData.append('chunk', chunk);
                formData.append('upload_id', uploadId);
                formData.append('filename', file.name);
                formData.append('chunk_index', i);
                formData.append('total_chunks', totalChunks);
                
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                if (!result.success) {
                    messageDiv.className = 'message error';
                    messageDiv.textContent = result.message;
                    return;
                }
                
                const progress = Math.round(((i + 1) / totalChunks) * 100);
                messageDiv.textContent = `A enviar... ${progress}%`;
            }
            
            const completeResponse = await fetch('/upload/complete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ upload_id: uploadId, filename: file.name })
            });
            
            const completeResult = await completeResponse.json();
            messageDiv.className = 'message ' + (completeResult.success ? 'success' : 'error');
            messageDiv.textContent = completeResult.message;
            
            if (completeResult.success) {
                fileInput.value = '';
                loadFiles();
            }
        });
        
        loadFiles();
    </script>
</body>
</html>
    ''')


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nenhum ficheiro selecionado'}), 400
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Apenas ficheiros ZIP são permitidos'}), 400
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        return jsonify({'success': True, 'message': f'Ficheiro {filename} enviado com sucesso!'})

    if 'chunk' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum chunk enviado'}), 400

    chunk = request.files['chunk']
    upload_id = request.form.get('upload_id')
    chunk_index = int(request.form.get('chunk_index', 0))
    total_chunks = int(request.form.get('total_chunks', 1))
    filename = request.form.get('filename', '')

    if not upload_id:
        return jsonify({'success': False, 'message': 'upload_id em falta'}), 400

    if not allowed_file(filename):
        return jsonify({'success': False, 'message': 'Apenas ficheiros ZIP são permitidos'}), 400

    chunk_dir = os.path.join(CHUNK_FOLDER, upload_id)
    os.makedirs(chunk_dir, exist_ok=True)

    chunk_path = os.path.join(chunk_dir, f"{chunk_index:05d}")
    chunk.save(chunk_path)

    return jsonify({'success': True, 'message': f'Chunk {chunk_index + 1}/{total_chunks} recebido'})


@app.route('/upload/complete', methods=['POST'])
def upload_complete():
    data = request.get_json()
    upload_id = data.get('upload_id')
    filename = data.get('filename', '')
    
    if not upload_id:
        return jsonify({'success': False, 'message': 'upload_id em falta'}), 400
    
    chunk_dir = os.path.join(CHUNK_FOLDER, upload_id)
    if not os.path.exists(chunk_dir):
        return jsonify({'success': False, 'message': 'Upload não encontrado'}), 404
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    final_filename = f"{timestamp}_{filename}"
    final_path = os.path.join(UPLOAD_FOLDER, final_filename)
    
    chunk_files = sorted(os.listdir(chunk_dir))
    
    with open(final_path, 'wb') as outfile:
        for chunk_name in chunk_files:
            chunk_path = os.path.join(chunk_dir, chunk_name)
            with open(chunk_path, 'rb') as infile:
                outfile.write(infile.read())
    
    for chunk_name in chunk_files:
        os.remove(os.path.join(chunk_dir, chunk_name))
    os.rmdir(chunk_dir)
    
    return jsonify({
        'success': True,
        'message': f'Ficheiro {final_filename} enviado com sucesso!'
    })


@app.route('/uploads')
def list_uploads():
    files = os.listdir(UPLOAD_FOLDER)
    return jsonify({'files': files})


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'success': True, 'message': f'Ficheiro {filename} eliminado'})
    return jsonify({'success': False, 'message': 'Ficheiro não encontrado'}), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
