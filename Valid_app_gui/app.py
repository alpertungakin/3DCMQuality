from flask import Flask, render_template, request, jsonify
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import time

app = Flask(__name__)

# Örnek veri
options = {
    'Validation ontology based on QIE 2016': 'Validation ontology based on QIE 2016',
    'Option 2': 'This is the content for Option 2.',
    'Option 3': 'This is the content for Option 3.',
}

@app.route('/')
def index():
    return render_template('index.html', options=options)

@app.route('/upload', methods=['POST'])
def upload():
    uploaded_file = request.files['file']
    if uploaded_file:
        file_content = uploaded_file.read().decode('utf-8')
        return file_content
    return 'No file uploaded'

@app.route('/get_content', methods=['POST'])
def get_content():
    selected_option = request.form.get('selected_option')
    content = options.get(selected_option, 'No content available for this option.')
    return content

@app.route('/process_texts', methods=['POST'])
def process_texts():
    text1 = request.form.get('text1')
    text2 = request.form.get('text2')
    combined_text = f"Processed text:\n\nText1:\n{text1}\n\nText2:\n{text2}"
    return jsonify({'response': combined_text})

if __name__ == '__main__':
    app.run(debug=True)
