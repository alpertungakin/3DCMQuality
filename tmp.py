import json
from shapely.geometry import Polygon
from rdflib import Graph, Literal, RDF, URIRef
from rdflib import Namespace
from rdflib.namespace import NamespaceManager, CSVW, DC, DCAT, DCTERMS, DOAP, FOAF, GEO, ODRL2, ORG, OWL, \
                           PROF, PROV, RDF, RDFS, SDO, SH, SKOS, SOSA, SSN, TIME, \
                           VOID, XMLNS, XSD
import numpy as np
import rdfpandas as rpd
import pandas as pd
import cjio as cj
from cjio import cityjson
import functions as func
from cityjson_bracket_cleaner import clean_json_file
from datetime import datetime

path_ = clean_json_file("DenHaag_01.city.json", "cleaned_{}.json".format(str(datetime.now().timestamp())))
# path_ = clean_json_file("Rotterdam.city.json", "cleaned_{}.json".format(str(datetime.now().timestamp())))

model = cityjson.load(path_)
cityObjIds = list(model.cityobjects.keys())

for obj in cityObjIds:
    if model.get_cityobjects()[obj].type == "Building":
        if model.get_cityobjects()[obj].attributes != {} :
            if "Solid" or "MultiSurface" in model.get_cityobjects()[obj].geometry[0].type:
                print(model.get_cityobjects()[obj].geometry[0].type)