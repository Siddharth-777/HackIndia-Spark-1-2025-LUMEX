import PyPDF2
import docx
import logging

def process_document(filepath):
    """Process different document types and extract text content"""
    try:
        file_extension = filepath.split('.')[-1].lower()
        
        if file_extension == 'pdf':
            return process_pdf(filepath)
        elif file_extension == 'docx':
            return process_docx(filepath)
        elif file_extension == 'txt':
            return process_txt(filepath)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
            
    except Exception as e:
        logging.error(f"Error processing document: {str(e)}")
        raise

def process_pdf(filepath):
    """Extract text from PDF file"""
    text = ""
    with open(filepath, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def process_docx(filepath):
    """Extract text from DOCX file"""
    doc = docx.Document(filepath)
    text = []
    for paragraph in doc.paragraphs:
        text.append(paragraph.text)
    return '\n'.join(text)

def process_txt(filepath):
    """Read text from TXT file"""
    with open(filepath, 'r', encoding='utf-8') as file:
        return file.read()
