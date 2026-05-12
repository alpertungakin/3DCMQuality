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
import cityjson2glb
from cityjson_bracket_cleaner import clean_json_file


class _IdentityTransformer:
    # Passthrough used in place of an ECEF pyproj transformer so vertices stay
    # in the model's native CRS — ECEF inflates them to ~5e6 m, breaking float32
    # precision and producing a tilted "up" direction in the three.js viewer.
    @staticmethod
    def transform(x, y, z):
        return x, y, z


def _extract_epsg_from_reference_system(crs_str):
    """Pull the EPSG integer out of any of the formats CityJSON files use:
    "EPSG:2150", "urn:ogc:def:crs:EPSG::2150", or the OGC URL form
    "https://www.opengis.net/def/crs/EPSG/0/2150". cjio.get_epsg() handles the
    first two but not the URL — Vienna/Montreal models tend to use the URL."""
    if not crs_str:
        return None
    parts = re.split(r'[:/]', str(crs_str))
    for part in reversed(parts):
        if part.isdigit():
            return int(part)
    return None


# Last-resort EPSG lookup by city keyword. Triggered when cm.get_epsg() returns
# nothing and metadata.referenceSystem doesn't yield a code. Match is
# case-insensitive over metadata.title and metadata.identifier.
_CITY_EPSG_HINTS = {
    'vienna': 31256,
    'wien': 31256,
    'austria': 31256,
    'montreal': 2950,
    'quebec': 2950,
    'amsterdam': 28992,
    'rotterdam': 28992,
    'netherlands': 28992,
    'helsinki': 3879,
    'zurich': 2056,
    'zürich': 2056,
    'paris': 2154,
    'berlin': 25833,
    'munich': 25832,
    'münchen': 25832,
}


def _guess_epsg_from_metadata(metadata):
    """Look for city/country keywords in metadata.title/identifier so files
    with no referenceSystem still get a chance at a basemap."""
    if not metadata:
        return None
    haystack = ' '.join(
        str(metadata.get(k, '')) for k in ('title', 'identifier', 'datasetTopicCategory')
    ).lower()
    for keyword, epsg in _CITY_EPSG_HINTS.items():
        if keyword in haystack:
            return epsg
    return None

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECEIVED_DIR = os.path.join(BASE_DIR, 'received')
RDFS_DIR = os.path.join(BASE_DIR, 'rdfs')
RESULTS_DIR = os.path.join(BASE_DIR, 'results')
for _d in (RECEIVED_DIR, RDFS_DIR, RESULTS_DIR):
    os.makedirs(_d, exist_ok=True)

#SHACL for CityJSON validation
ontodirec = os.path.join(BASE_DIR, 'ontologies', "shacl4cg_v2.ttl")
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
        ts = datetime.datetime.now().timestamp()
        # Save the uploaded file temporarily
        temp_file_path = os.path.join(RECEIVED_DIR, 'temp_cityjson_{}.json'.format(ts))
        uploaded_file.save(temp_file_path)
        print("File saved temporarily")  # Debugging

        # Run the same bracket-stripping pass that json2rdf does, so the OBJ_ID
        # values baked into the GLB property table match the bare-UUID IDs in
        # the URI list (which come from the /process_texts → json2rdf path).
        # Otherwise IDs like "{0031458C-...}" on the GLB side and "0031458C-..."
        # on the URI side never match and feature highlighting fails.
        cleaned_path = clean_json_file(
            temp_file_path,
            os.path.join(RECEIVED_DIR, 'cleaned_temp_{}.json'.format(ts)),
        )

        # Parse the CityJSON file. Use cityjson.load (not cityjson.reader) so
        # cm.load_from_j() runs and dereferences boundaries into coordinate
        # triples — cityjson2glb's writer iterates real coords, not vertex indices.
        cm = cityjson.load(cleaned_path)
        print("CityJSON parsed successfully")  # Debugging

        # Generate a unique filename
        fileNameGLB = f"{request.remote_addr}_{ts}.glb"
        direcGLB = os.path.join(RECEIVED_DIR, fileNameGLB)

        # Export to GLB using the local cityjson2glb writer. We pass an identity
        # transformer (no ECEF reprojection) and let glb_writer recenter the
        # vertices around the model centroid so coordinates stay small.
        city_objects = list(cm.cityobjects.keys())
        centroid = cityjson2glb.cityjson_to_glb(city_objects, cm, _IdentityTransformer(), direcGLB)
        if not os.path.exists(direcGLB):
            raise RuntimeError("cityjson2glb did not produce an output file")
        print("GLB file written successfully")  # Debugging

        # Transform the recentering centroid to WGS84 so the frontend can drop
        # an OSM basemap under the model. Logs reasons for skipping so the
        # browser console can show "no basemap was added because…" when this
        # silently returns null lat/lng.
        import math
        lat = None
        lng = None
        if centroid is None:
            print("[basemap] cityjson2glb did not return a centroid; skipping")
        elif not all(math.isfinite(c) for c in centroid):
            print(f"[basemap] centroid has non-finite components: {centroid}; skipping")
        else:
            try:
                import pyproj

                # Resolution order:
                #   1. Explicit override from the client form (`epsg`).
                #   2. cjio's parser (handles "EPSG:N" and "urn:...EPSG::N").
                #   3. Manual regex on metadata.referenceSystem (handles the
                #      "https://www.opengis.net/def/crs/EPSG/0/N" URL form).
                #   4. City-keyword guesser over metadata.title/identifier.
                # Step 1 — request override.
                client_epsg = (request.form.get('epsg') or '').strip()
                epsg = None
                if client_epsg.isdigit():
                    epsg = int(client_epsg)
                    print(f"[basemap] EPSG override from client: {epsg}")

                # Step 2 — cjio's own parser.
                if not epsg:
                    epsg = cm.get_epsg()

                # Step 3 — raw referenceSystem (URL form).
                raw_ref = None
                if not epsg:
                    try:
                        raw_ref = cm.j.get('metadata', {}).get('referenceSystem')
                        epsg = _extract_epsg_from_reference_system(raw_ref)
                        if epsg:
                            print(f"[basemap] EPSG parsed from referenceSystem={raw_ref!r}: {epsg}")
                    except Exception as parse_err:
                        print(f"[basemap] failed reading metadata.referenceSystem: {parse_err}")

                # Step 4 — city-keyword guesser. Dump full metadata + transform
                # so the user can pick an override if our guess is wrong.
                if not epsg:
                    md = cm.j.get('metadata') or {}
                    tf = cm.j.get('transform') or {}
                    print(f"[basemap] metadata={md}")
                    print(f"[basemap] transform={tf}")
                    epsg = _guess_epsg_from_metadata(md)
                    if epsg:
                        print(f"[basemap] EPSG guessed from city keyword in metadata: {epsg}")
                    else:
                        print("[basemap] no EPSG hint found in metadata; pass `epsg` form field to override")

                print(f"[basemap] centroid={centroid}, EPSG={epsg}")
                if not epsg:
                    print("[basemap] no EPSG available; skipping")
                else:
                    to_wgs = pyproj.Transformer.from_crs(epsg, 4326, always_xy=True)
                    # Some CityJSON files declare a 2.5D/compound CRS; pyproj
                    # then expects three inputs. Try 3D first, fall back to 2D.
                    try:
                        result = to_wgs.transform(centroid[0], centroid[1], centroid[2])
                        lng, lat = result[0], result[1]
                    except Exception:
                        lng, lat = to_wgs.transform(centroid[0], centroid[1])
                    if not (math.isfinite(lat) and math.isfinite(lng)):
                        print(f"[basemap] pyproj returned non-finite (lat={lat}, lng={lng}); skipping")
                        lat, lng = None, None
                    else:
                        print(f"[basemap] -> lat={lat}, lng={lng}")
            except Exception as proj_err:
                print(f"[basemap] centroid → WGS84 failed: {proj_err}")

        return jsonify({
            'response': fileNameGLB,
            'lat': lat,
            'lng': lng,
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
    return send_from_directory(RECEIVED_DIR, filename, as_attachment=False)

@app.route('/process_texts', methods=['POST'])
def process_texts():
    text1 = request.form.get('cityjson')
    text2 = request.form.get('ontology')
    fileNameRDF = request.remote_addr + "_" + str(datetime.datetime.now().timestamp())
    direc1 = os.path.join(RECEIVED_DIR, fileNameRDF + ".city" + ".json")
    filepath = open(direc1, "w")
    filepath.write(text1)
    filepath.close()
    print(direc1)
    rdfGraph = json2rdf.main(direc1)
    direc2 = os.path.join(RDFS_DIR, "{}.ttl".format(fileNameRDF))
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

    direc4 = ontodirec = os.path.join(RESULTS_DIR, "report_{}.txt".format(fileNameRDF))
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
