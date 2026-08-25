# app/pdf_utils.py
import os
from io import BytesIO
from pathlib import Path
from PIL import Image
import PyPDF2
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
import img2pdf
from pdf2image import convert_from_bytes

# === CONFIGURATION ===
# For Windows - specify your Poppler path
POPPLER_PATH = r'C:\Users\Shruti\Downloads\poppler-26.02.0\Library\bin'

# For Mac/Linux, this will be None and pdf2image will auto-detect
# POPPLER_PATH = None  # Uncomment if on Mac/Linux

def get_poppler_path():
    """
    Returns the Poppler path based on OS.
    Windows: Uses the specified path
    Mac/Linux: Returns None (auto-detect)
    """
    if os.name == 'nt':  # Windows
        return POPPLER_PATH
    else:  # Mac/Linux
        return None

# === PDF GENERATION ===

def create_pdf_from_text(text, filename="document.pdf"):
    """
    Create a PDF from text string (memory-based)
    Returns: BytesIO object containing the PDF
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, text)
    c.save()
    buffer.seek(0)
    return buffer

def create_pdf_from_image(image_bytes_list):
    """
    Create PDF from list of image bytes
    Returns: BytesIO object containing the PDF
    """
    # Convert image bytes to PIL Images first
    images = []
    for img_bytes in image_bytes_list:
        img = Image.open(BytesIO(img_bytes))
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        images.append(img)
    
    buffer = BytesIO()
    # Save first image as PDF, append others
    if images:
        images[0].save(
            buffer,
            "PDF",
            save_all=True,
            append_images=images[1:] if len(images) > 1 else None,
            resolution=100.0
        )
    buffer.seek(0)
    return buffer

# === PDF TO IMAGES ===

def pdf_to_images(pdf_bytes):
    """
    Convert PDF bytes to list of PIL Images
    Returns: List of PIL Image objects
    """
    poppler_path = get_poppler_path()
    images = convert_from_bytes(
        pdf_bytes,
        poppler_path=poppler_path,
        dpi=200  # Quality setting
    )
    return images

def pdf_to_images_bytes(pdf_bytes, format='PNG'):
    """
    Convert PDF bytes to list of image bytes
    Returns: List of BytesIO objects (images)
    """
    images = pdf_to_images(pdf_bytes)
    image_bytes_list = []
    for img in images:
        buffer = BytesIO()
        img.save(buffer, format=format)
        buffer.seek(0)
        image_bytes_list.append(buffer)
    return image_bytes_list

# === PDF MANIPULATION ===

def merge_pdfs(pdf_bytes_list):
    """
    Merge multiple PDFs from bytes
    Returns: BytesIO object containing merged PDF
    """
    writer = PdfWriter()
    for pdf_bytes in pdf_bytes_list:
        reader = PdfReader(BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    
    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer

def split_pdf(pdf_bytes, start_page, end_page):
    """
    Extract specific pages from PDF
    Returns: BytesIO object containing extracted pages
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    
    # Convert to 0-based indexing
    start_idx = start_page - 1
    end_idx = min(end_page, len(reader.pages))
    
    for i in range(start_idx, end_idx):
        writer.add_page(reader.pages[i])
    
    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer

def extract_page_count(pdf_bytes):
    """
    Get total number of pages in PDF
    Returns: Integer
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    return len(reader.pages)

# === PDF LOCKING/ENCRYPTION ===

def lock_pdf(pdf_bytes, password):
    """
    Add password protection to PDF
    Returns: BytesIO object containing encrypted PDF
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    
    for page in reader.pages:
        writer.add_page(page)
    
    writer.encrypt(password)
    
    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer

def unlock_pdf(pdf_bytes, password):
    """
    Remove password protection from PDF
    Returns: BytesIO object containing decrypted PDF
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    
    # Try to decrypt
    if reader.is_encrypted:
        reader.decrypt(password)
    
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    
    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer

# === PDF ROTATION ===

def rotate_pdf(pdf_bytes, rotation_angle):
    """
    Rotate all pages in PDF
    rotation_angle: 90, 180, 270
    Returns: BytesIO object containing rotated PDF
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    
    for page in reader.pages:
        page.rotate(rotation_angle)
        writer.add_page(page)
    
    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer

# === IMAGE TO PDF (from image bytes) ===

def images_to_pdf_bytes(image_bytes_list):
    """
    Convert multiple images to single PDF
    Returns: BytesIO object containing PDF
    """
    # img2pdf works directly with bytes
    pdf_bytes = img2pdf.convert(image_bytes_list)
    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    return buffer

# === EXTRACT TEXT ===

# app/pdf_utils.py - Replace the existing extract_text function
import pdfplumber

def extract_text(pdf_bytes):
    """
    Extract text from PDF preserving proper formatting
    """
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        all_text = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text.append(text)
        return '\n\n'.join(all_text)

# === PDF COMPRESSION (basic) ===

def compress_pdf(pdf_bytes):
    """
    Basic compression by re-saving with compression
    Returns: BytesIO object containing compressed PDF
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    
    for page in reader.pages:
        writer.add_page(page)
    
    # Enable compression
    writer.compress_content_streams = True
    
    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer