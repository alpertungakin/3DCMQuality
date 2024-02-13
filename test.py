# -*- coding: utf-8 -*-
"""
Created on Thu Oct 19 15:02:58 2023

@author: alper
"""

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

with open("DenHaag_01.city.json") as file:
    plain = json.load(file)
    
rootSpace = "http://example.org/#"
CityGML_URI = "http://www.theworldavatar.com/ontology/ontocitygml/OntoCityGML.owl#"

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
                surfacedf["{}_{}".format(obj,i)]["geometry"] = Polygon(geometry.boundaries[0][i][0]).wkt
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
                try:
                    surfacedf["{}_{}".format(obj,i)]["geometry"] = Polygon(geometry.boundaries[i][0]).wkt
                except TypeError:
                    surfacedf["{}_{}".format(obj,i)]["geometry"] = Polygon(geometry.boundaries[i][0][0]).wkt

surfacedf = pd.DataFrame(surfacedf)
surfacedf = surfacedf.transpose()
namespace_manager = NamespaceManager(Graph())
surfaceG = rpd.graph.to_graph(surfacedf, namespace_manager)
surface_str = surfaceG.serialize(format = 'ttl')
modelG = rpd.graph.to_graph(modeldf, namespace_manager)
model_str = modelG.serialize(format = 'ttl')
surfaceTriples_t = list(surfaceG.triples((None,None,None)))
modelTriples_t = list(modelG.triples((None,None,None)))
modelTriples = []
surfaceTriples = []
for t in modelTriples_t:
    modelTriples.append([t[0].value, t[1].value, t[2].value])
for s in surfaceTriples_t:
    surfaceTriples.append([s[0].value, s[1].value, s[2].value])

del t,s

hasGeometryRels = []
for t in modelTriples:
    for s in surfaceTriples:
        if s[2] == t[0]:
            hasGeometryRels.append([t[0], "hasGeometry", s[0]])
modelTriples = modelTriples + hasGeometryRels


# rdf merge
# pgraph to linked
