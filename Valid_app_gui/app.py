from flask import Flask, render_template, request, jsonify
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import time
import json2rdf

app = Flask(__name__)

#SHACL for CityJSON validation
valpath = open("shacl4cg_v2.ttl", "r")
shacl4cg = valpath.read()
valpath.close()

# Örnek veri
options = {
    'Validation ontology based on QIE 2016': shacl4cg,
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

@app.route('/process_texts', methods=['POST'])
def process_texts():
    text1 = request.form.get('cityjson')
    text2 = request.form.get('ontology')
    content = options.get(text2, 'No content available for this option.')
    print(content)
    combined_text = f"Processed text:\n\nText1:\n{text1}\n\nText2:\n{content}"
    return jsonify({'response': combined_text})

if __name__ == '__main__':
    app.run(debug=False)
