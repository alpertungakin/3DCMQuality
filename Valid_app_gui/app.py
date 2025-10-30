from flask import Flask, render_template, request, jsonify, send_from_directory

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import time
from datetime import datetime
import json2rdf
from werkzeug.utils import secure_filename
import datetime
from pyshacl import validate
from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import NamespaceManager, CSVW, DC, DCAT, DCTERMS, DOAP, FOAF, GEO, ODRL2, ORG, OWL, \
                           PROF, PROV, RDF, RDFS, SDO, SH, SKOS, SOSA, SSN, TIME, \
                           VOID, XMLNS, XSD
import re
import json
import cjio as cj
from cjio import cityjson
import io
import base64

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

@app.route('/results', methods=['GET'])
def results_page():
    return render_template('responsetxt.html')

@app.route('/upload', methods=['POST'])
def upload():
    uploaded_file = request.files['file']
    if uploaded_file:
        file_content = uploaded_file.read().decode('utf-8')
        return file_content
    return 'No file uploaded'

@app.route('/get_gltf', methods=['POST'])
def get_gltf():
    uploaded_file = request.files.get('file')
    if not uploaded_file:
        return jsonify({'error': 'No file provided'}), 400

    try:
        # Save the uploaded file temporarily
        temp_file_path = os.path.join('received', 'temp_cityjson_{}.json'.format(currDate.timestamp()))
        uploaded_file.save(temp_file_path)
        print("File saved temporarily")  # Debugging

        # Parse the CityJSON file
        with open(temp_file_path, "r", encoding="utf-8-sig") as f:
            cm = cityjson.reader(file=f)
        print("CityJSON parsed successfully")  # Debugging

        # Export to GLB
        glb_data = cm.export2glb()
        print("GLB export successful")  # Debugging

        # Generate a unique filename
        fileNameGLB = f"{request.remote_addr}_{currDate.timestamp()}.glb"
        direcGLB = os.path.join('received', fileNameGLB)

        # Write the GLB data to a file
        with open(direcGLB, "wb") as glb_file:
            glb_file.write(glb_data.getvalue())
        print("GLB file written successfully")  # Debugging
        # glb_base64 = base64.b64encode(glb_data.getvalue()).decode('utf-8')
        # Clean up the temporary file
        # return jsonify({
        #     'response': {
        #         'glbBase64': glb_base64,
        #         'fileName': f"{request.remote_addr}_{currDate.timestamp()}.glb"
        #     }
        # })
        return jsonify({
            'response' : fileNameGLB
        })

    except UnicodeDecodeError as e:
        print(f"UnicodeDecodeError: {str(e)}")  # Debugging
        return jsonify({'error': 'Invalid file encoding. Please upload a valid CityJSON file.'}), 400
    except Exception as e:
        print(f"Error processing GLB export: {str(e)}")  # Debugging
        return jsonify({'error': f'Failed to process the file: {str(e)}'}), 500
    
@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    # Serve files from the 'received' directory
    return send_from_directory('received', filename, as_attachment=False)

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
    rdfTurtle = rdfGraph.serialize(direc2, "ttl")  

    # direc2 = os.path.join('rdfs', "{}.ttl".format(fileNameRDF))
    # with open(direc2, "w") as f:
    #     f.write(rdfTurtle)

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

    with open(direc2, "r", encoding="utf-8") as file:
        ttl_text = file.read()
    
    # direc4 = os.path.join('results', "report_{}.txt".format(fileNameRDF))
    # with open(direc4, "w") as val:
    #     val.write(results_text)

    print(type(ttl_text))  # Should output: <class 'str'>
    return jsonify({'response': results_text, 'rdf': ttl_text})

@app.route('/visualize', methods=['POST'])
def visualize():
    # Get the JSON payload from the request
    payload = request.get_json()

    # Extract the SHACL and RDF data
    toParseSHACL = payload.get('shacl')
    toParseRDF = payload.get('rdf')
    focus_node_pattern = re.compile(r'Focus Node: (\S+)')
    EX = Namespace("http://example.org/#")
    CITYGML = Namespace("http://www.theworldavatar.com/ontology/ontocitygml/OntoCityGML.owl#")
    GEO = Namespace("http://www.opengis.net/ont/geosparql#")
    unique_focus_nodes = set()
    unique_parents = set()

    for line in toParseSHACL.splitlines():
        if "Focus Node:" in line:
            match = focus_node_pattern.search(line)
            if match:
                focus_node_uri = match.group(1)
                unique_focus_nodes.add(URIRef(EX + "{}".format(focus_node_uri.split(":")[1])))

    g = Graph()
    g.parse(data = toParseRDF, format="turtle")
    print(CITYGML.parent)

    childs = {}
    geometries = {}

    for focus_node in unique_focus_nodes:
        for s, p, o in g.triples((focus_node, CITYGML.parent, None)):
            unique_parents.add(o)
        for s1,p1,o1 in g.triples((focus_node, GEO.asWKT, None)):
            geometries[s1] = o1

    for parent in unique_parents:
        temp = []
        for s, p, o in g.triples((parent, GEO.hasGeometry, None)):
            temp.append(o)
        childs[s] = temp

    merged_dict = {k: [geometries[item] for item in v if item in geometries] for k, v in childs.items()}

    return jsonify({'response': merged_dict})

if __name__ == '__main__':
    app.run(debug=True)
