from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
import html
from pathlib import Path

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/html_files'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB限制

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    """主页面"""
    return render_template('editor.html')

@app.route('/list_files')
def list_files():
    """列出所有HTML文件"""
    files = []
    for f in os.listdir(app.config['UPLOAD_FOLDER']):
        if f.endswith('.html'):
            files.append({
                'name': f,
                'path': f'/static/html_files/{f}',
                'size': os.path.getsize(f'{app.config["UPLOAD_FOLDER"]}/{f}')
            })
    return jsonify(files)

@app.route('/upload', methods=['POST'])
def upload_file():
    """上传HTML文件"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and file.filename.endswith('.html'):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({'success': True, 'filename': filename})
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/save', methods=['POST'])
def save_file():
    """保存编辑后的HTML"""
    data = request.json
    filename = secure_filename(data.get('filename'))
    content = data.get('content', '')
    
    if not filename.endswith('.html'):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        with open(f'{app.config["UPLOAD_FOLDER"]}/{filename}', 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export/<filename>')
def export_file(filename):
    """导出HTML文件"""
    safe_filename = secure_filename(filename)
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        safe_filename,
        as_attachment=True
    )

@app.route('/preview/<filename>')
def preview_file(filename):
    """预览HTML文件"""
    safe_filename = secure_filename(filename)
    filepath = Path(app.config['UPLOAD_FOLDER']) / safe_filename
    
    if not filepath.exists():
        return "File not found", 404
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 转义内容防止XSS，实际预览时会取消转义
    escaped_content = html.escape(content)
    return render_template('preview.html', 
                         filename=safe_filename,
                         content=escaped_content)

if __name__ == '__main__':
    app.run(debug=True, port=5000)