# app/main.py
import os
import base64
from io import BytesIO
from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import tempfile

from app.pdf_utils import (
    create_pdf_from_text,
    create_pdf_from_image,
    pdf_to_images,
    pdf_to_images_bytes,
    merge_pdfs,
    split_pdf,
    extract_page_count,
    lock_pdf,
    unlock_pdf,
    rotate_pdf,
    images_to_pdf_bytes,
    extract_text,
    compress_pdf
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# === ROUTES ===

@app.route('/')
def index():
    """Home page with all tools"""
    return render_template('index.html')

@app.route('/tools')
def tools():
    """Alternative: List all available tools"""
    return render_template('tools.html')

# === IMAGE TO PDF ===

@app.route('/image-to-pdf', methods=['GET', 'POST'])
def image_to_pdf_route():
    if request.method == 'POST':
        if 'files' not in request.files:
            return render_template('error.html', error='No files uploaded'), 400
        
        files = request.files.getlist('files')
        if len(files) == 0:
            return render_template('error.html', error='No files selected'), 400
        
        try:
            image_bytes_list = []
            for file in files:
                if file.filename == '':
                    continue
                if allowed_file(file.filename):
                    image_bytes_list.append(file.read())
            
            if not image_bytes_list:
                return render_template('error.html', error='No valid images uploaded'), 400
            
            pdf_buffer = images_to_pdf_bytes(image_bytes_list)
            
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name='converted_images.pdf'
            )
        except Exception as e:
            return render_template('error.html', error=f'Error converting images: {str(e)}'), 500
    
    return render_template('image_to_pdf.html')

# === MERGE PDF ===

@app.route('/merge-pdf', methods=['GET', 'POST'])
def merge_pdf_route():
    if request.method == 'POST':
        if 'files' not in request.files:
            return render_template('error.html', error='No files uploaded'), 400
        
        files = request.files.getlist('files')
        if len(files) < 2:
            return render_template('error.html', error='Please upload at least 2 PDFs to merge'), 400
        
        try:
            pdf_bytes_list = []
            for file in files:
                if file.filename == '':
                    continue
                if file.filename.endswith('.pdf'):
                    pdf_bytes_list.append(file.read())
            
            if len(pdf_bytes_list) < 2:
                return render_template('error.html', error='Please upload at least 2 valid PDFs'), 400
            
            merged_buffer = merge_pdfs(pdf_bytes_list)
            
            return send_file(
                merged_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name='merged.pdf'
            )
        except Exception as e:
            return render_template('error.html', error=f'Error merging PDFs: {str(e)}'), 500
    
    return render_template('merge_pdf.html')

# === SPLIT PDF ===

@app.route('/split-pdf', methods=['GET', 'POST'])
def split_pdf_route():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('error.html', error='No file uploaded'), 400
        
        file = request.files['file']
        if file.filename == '':
            return render_template('error.html', error='No file selected'), 400
        
        if not file.filename.endswith('.pdf'):
            return render_template('error.html', error='Please upload a PDF file'), 400
        
        try:
            start_page = int(request.form.get('start_page', 1))
            end_page = int(request.form.get('end_page', 1))
            
            if start_page < 1 or end_page < start_page:
                return render_template('error.html', error='Invalid page range'), 400
            
            pdf_bytes = file.read()
            total_pages = extract_page_count(pdf_bytes)
            
            if end_page > total_pages:
                return render_template('error.html', error=f'PDF has only {total_pages} pages'), 400
            
            split_buffer = split_pdf(pdf_bytes, start_page, end_page)
            
            return send_file(
                split_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'split_pages_{start_page}-{end_page}.pdf'
            )
        except Exception as e:
            return render_template('error.html', error=f'Error splitting PDF: {str(e)}'), 500
    
    return render_template('split_pdf.html')

# === LOCK PDF ===

@app.route('/lock-pdf', methods=['GET', 'POST'])
def lock_pdf_route():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('error.html', error='No file uploaded'), 400
        
        file = request.files['file']
        if file.filename == '':
            return render_template('error.html', error='No file selected'), 400
        
        if not file.filename.endswith('.pdf'):
            return render_template('error.html', error='Please upload a PDF file'), 400
        
        password = request.form.get('password', '')
        if len(password) < 4:
            return render_template('error.html', error='Password must be at least 4 characters'), 400
        
        try:
            pdf_bytes = file.read()
            locked_buffer = lock_pdf(pdf_bytes, password)
            
            return send_file(
                locked_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'locked_{file.filename}'
            )
        except Exception as e:
            return render_template('error.html', error=f'Error locking PDF: {str(e)}'), 500
    
    return render_template('lock_pdf.html')

# === UNLOCK PDF ===

@app.route('/unlock-pdf', methods=['GET', 'POST'])
def unlock_pdf_route():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('error.html', error='No file uploaded'), 400
        
        file = request.files['file']
        if file.filename == '':
            return render_template('error.html', error='No file selected'), 400
        
        if not file.filename.endswith('.pdf'):
            return render_template('error.html', error='Please upload a PDF file'), 400
        
        password = request.form.get('password', '')
        if len(password) < 1:
            return render_template('error.html', error='Please enter the password'), 400
        
        try:
            pdf_bytes = file.read()
            unlocked_buffer = unlock_pdf(pdf_bytes, password)
            
            return send_file(
                unlocked_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'unlocked_{file.filename}'
            )
        except Exception as e:
            return render_template('error.html', error=f'Error unlocking PDF: {str(e)}'), 500
    
    return render_template('unlock_pdf.html')

# === ROTATE PDF ===

@app.route('/rotate-pdf', methods=['GET', 'POST'])
def rotate_pdf_route():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('error.html', error='No file uploaded'), 400
        
        file = request.files['file']
        if file.filename == '':
            return render_template('error.html', error='No file selected'), 400
        
        if not file.filename.endswith('.pdf'):
            return render_template('error.html', error='Please upload a PDF file'), 400
        
        rotation = int(request.form.get('rotation', 90))
        if rotation not in [90, 180, 270]:
            return render_template('error.html', error='Rotation must be 90, 180, or 270 degrees'), 400
        
        try:
            pdf_bytes = file.read()
            rotated_buffer = rotate_pdf(pdf_bytes, rotation)
            
            return send_file(
                rotated_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'rotated_{rotation}_{file.filename}'
            )
        except Exception as e:
            return render_template('error.html', error=f'Error rotating PDF: {str(e)}'), 500
    
    return render_template('rotate_pdf.html')

# === EXTRACT TEXT ===

@app.route('/extract-text', methods=['GET', 'POST'])
def extract_text_route():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('error.html', error='No file uploaded'), 400
        
        file = request.files['file']
        if file.filename == '':
            return render_template('error.html', error='No file selected'), 400
        
        if not file.filename.endswith('.pdf'):
            return render_template('error.html', error='Please upload a PDF file'), 400
        
        try:
            pdf_bytes = file.read()
            text = extract_text(pdf_bytes)
            
            return render_template('result_text.html', text=text, filename=file.filename)
        except Exception as e:
            return render_template('error.html', error=f'Error extracting text: {str(e)}'), 500
    
    return render_template('extract_text.html')

# === CREATE PDF FROM TEXT ===

@app.route('/create-pdf', methods=['GET', 'POST'])
def create_pdf_route():
    if request.method == 'POST':
        text = request.form.get('text', '')
        if len(text) < 1:
            return render_template('error.html', error='Please enter some text'), 400
        
        try:
            pdf_buffer = create_pdf_from_text(text)
            
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name='created.pdf'
            )
        except Exception as e:
            return render_template('error.html', error=f'Error creating PDF: {str(e)}'), 500
    
    return render_template('create_pdf.html')

# === ERROR HANDLER ===

@app.errorhandler(413)
def too_large(e):
    return render_template('error.html', error='File too large. Maximum size is 50MB.'), 413

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found'), 404

# === RUN APP ===
app = app

# For local development
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)