from flask import Flask, render_template, request, jsonify

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import time
import json2rdf
from werkzeug.utils import secure_filename
import datetime
from pyshacl import validate
from rdflib import Graph, Literal, RDF, URIRef
from rdflib.namespace import NamespaceManager, CSVW, DC, DCAT, DCTERMS, DOAP, FOAF, GEO, ODRL2, ORG, OWL, \
                           PROF, PROV, RDF, RDFS, SDO, SH, SKOS, SOSA, SSN, TIME, \
                           VOID, XMLNS, XSD
                           


currDate = datetime.datetime.now()
app = Flask(__name__)

#SHACL for CityJSON validation
ontodirec = os.path.join('ontologies', "shacl4cg_v2.ttl")
#valpath = open(ontodirec, "r")
#shacl4cg = valpath.read()
#valpath.close()

# Örnek veri
options = {
    'Validation ontology based on QIE 2016': ontodirec,
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
    fileNameRDF = request.remote_addr + "_" + str(currDate.timestamp())
    direc1 = os.path.join('received', fileNameRDF + ".city" + ".json")
    filepath = open(direc1, "w")
    filepath.write(text1)
    filepath.close()
    print(direc1)
    rdfGraph = json2rdf.main(direc1)
    direc2 = os.path.join('rdfs', "{}.ttl".format(fileNameRDF))
    rdfGraph.serialize(direc2, "ttl")  
    direc3 = options.get(text2, 'No content available for this option.')

    data_graph = Graph()
    data_graph.parse(direc2, format='turtle')

    shacl_graph = Graph()
    shacl_graph.parse(direc3, format='turtle')
    r = validate(data_graph,
        shacl_graph=shacl_graph,
        ont_graph=None,
        inference='none',
        abort_on_first=False,
        allow_infos=False,
        allow_warnings=False,
        meta_shacl=False,
        advanced=False,
        js=False,
        debug=False)

    validity, results_graph, results_text = r

    direc4 = ontodirec = os.path.join('results', "report_{}.txt".format(fileNameRDF))
    val = open(direc4, "w")
    val.write(results_text)
    val.close()
    #print(content)
    #rdfGraph = json2rdf(text1)

    #combined_text = f"Processed text:\n\nText1:\n{text1}\n\nText2:\n{content}"
    return jsonify({'response': results_text})

if __name__ == '__main__':
    app.run(debug=True)
