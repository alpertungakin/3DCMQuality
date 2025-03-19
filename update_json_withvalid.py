import cjio as cj
from cjio import cityjson
import re
from rdflib import Graph, Literal, RDF, URIRef
from rdflib import Namespace
from copy import deepcopy

data_graph = Graph()
data_graph.parse("rotterdam_rdf.ttl", format='turtle')

with open('validation_results.txt', 'r', encoding='utf-8') as file:
    toParseSHACL = file.read()

toParseSHACL_ = toParseSHACL.splitlines()


model = cityjson.load("Rotterdam.city.json")
focus_node_pattern = re.compile(r'Focus Node: (\S+)')
EX = Namespace("http://example.org/#")
CITYGML = Namespace("http://www.theworldavatar.com/ontology/ontocitygml/OntoCityGML.owl#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
unique_focus_nodes = set()
unique_parents = set()

# for line in toParseSHACL.splitlines():
#     if "Focus Node:" in line:
#         match = focus_node_pattern.search(line)
#         if match:
#             focus_node_uri = match.group(1)
#             unique_focus_nodes.add(URIRef(EX + "{}".format(focus_node_uri.split(":")[1])))

# for focus_node in unique_focus_nodes:
#     for s, p, o in data_graph.triples((focus_node, CITYGML.parent, None)):
#         unique_parents.add(str(o).split("#")[1])

cm_copy = deepcopy(model)

nonWTParents = set()
for i in range(len(toParseSHACL_) - 1):  # -1 to avoid index out of range
    if "Source Shape: citygml:SolidType-isWatertight" in toParseSHACL_[i] and "Focus Node:" in toParseSHACL_[i + 1]:
        print(toParseSHACL_[i + 1])
        nonWTParents.add(toParseSHACL_[i + 1].split(" ex:")[1])


for co_id, co in cm_copy.cityobjects.items():
    if co_id.strip("{}") in nonWTParents:
        co.attributes['isWatertight'] = '0'
    else:
        co.attributes['isWatertight'] = '1'

cityjson.save(cm_copy, "Rotterdam_validity.city.json")
