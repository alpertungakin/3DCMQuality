# -*- coding: utf-8 -*-
"""
Created on Thu Oct 19 15:02:58 2023

@author: alper
"""

import json
# from shapely.geometry import Polygon, Point, LineString
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
import time

start = time.time()
with open("DenHaag_01.city.json") as file:
    plain = json.load(file)
    
model = cityjson.load("DenHaag_01.city.json")
modeldf = model.to_dataframe()

cityObjIds = list(model.cityobjects.keys())
geometryTypes = {}
objectTypes = {}
parents = {}

for obj in cityObjIds:
    
    if len(model.get_cityobjects()[obj].parents) == 0:
        parents[obj] = "CityModel"
    else:
        parents[obj] = model.get_cityobjects()[obj].parents       
    if model.get_cityobjects()[obj].type == "BuildingPart":
        geometryTypes[obj] = "lod" + model.get_cityobjects()[obj].geometry[0].lod + model.get_cityobjects()[obj].geometry[0].type
        objectTypes[obj] = model.get_cityobjects()[obj].type
    elif model.get_cityobjects()[obj].type == "Building":
        geometryTypes[obj] = "None"
        objectTypes[obj] = model.get_cityobjects()[obj].type
    else:
        geometryTypes[obj] = model.get_cityobjects()[obj].geometry[0].type
        objectTypes[obj] = model.get_cityobjects()[obj].type        

modeldf["objectTypes"] = objectTypes
modeldf["geometryTypes"] = geometryTypes
modeldf["parents"] = parents

surfacedf = {}

for obj in cityObjIds:
    if model.get_cityobjects()[obj].type == "BuildingPart":
        for geometry in model.get_cityobjects()[obj].geometry:
            for i in range(len(geometry.boundaries[0])):
                surfacedf["{}_{}".format(obj,i)] = {}
                surfacedf["{}_{}".format(obj,i)]["parent"] = obj
                surfacedf["{}_{}".format(obj,i)]["geometry"] = str(geometry.boundaries[0][i][0])
                surfacedf["{}_{}".format(obj,i)]["semantic"] = geometry.surfaces[i]["type"]
                if "attributes" in geometry.surfaces[i]:
                   surfacedf["{}_{}".format(obj,i)]["normal"] =  geometry.surfaces[i]["attributes"]["Direction"]
                   surfacedf["{}_{}".format(obj,i)]["slope"] = geometry.surfaces[i]["attributes"]["Slope"]
                else:
                    pass
    elif model.get_cityobjects()[obj].type != "Building" or model.get_cityobjects()[obj].type != "BuildingPart":
        for geometry in model.get_cityobjects()[obj].geometry:
            for i in range(len(geometry.boundaries)):
                surfacedf["{}_{}".format(obj,i)] = {}
                surfacedf["{}_{}".format(obj,i)]["parent"] = obj
                surfacedf["{}_{}".format(obj,i)]["geometry"] = str(geometry.boundaries[i][0])
                
surfacedf = pd.DataFrame(surfacedf)
surfacedf = surfacedf.transpose()

namespace_manager = NamespaceManager(Graph())
namespace_manager.bind('skos', SKOS)
namespace_manager.bind('rdfpandas', Namespace('http://github.com/cadmiumkitty/rdfpandas/'))
modelGraph = rpd.graph.to_graph(modeldf, namespace_manager)
surfaceGraph = rpd.graph.to_graph(surfacedf, namespace_manager)
s = surfaceGraph.serialize(format = 'ttl')
g = modelGraph.serialize(format = 'ttl')
end = time.time()
print("--- %s seconds ---" % (end - start))
# str to WKT
# rdf merge
# pgraph to linked

