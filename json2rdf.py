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
from functions import getNormal, getTotalHeight, flattenSubBounds
    
def main(path):
    EXA = "http://example.org/#"
    CGML_URI = "http://www.theworldavatar.com/ontology/ontocitygml/OntoCityGML.owl#"
    SF_URI = "http://www.opengis.net/ont/sf#"
    BREP_URI = "https://github.com/OntoBREP/ontobrep/blob/master/owl/ontobrep.owl#"
    model = cityjson.load(path)
    modeldf = model.to_dataframe()
    
    cityObjIds = list(model.cityobjects.keys())
    geometryTypes = {}
    objectTypes = {}
    parents = {}
    totalHeights = {}

    for obj in cityObjIds:
        
        if len(model.get_cityobjects()[obj].parents) == 0:
            parents[obj] = "CityModel"
        else:
            parents[obj] = model.get_cityobjects()[obj].parents[0]       
        if model.get_cityobjects()[obj].type == "BuildingPart":
            geometryTypes[obj] = "lod" + model.get_cityobjects()[obj].geometry[0].lod + model.get_cityobjects()[obj].geometry[0].type
            objectTypes[obj] = model.get_cityobjects()[obj].type
            totalHeights[obj] = getTotalHeight(model.get_cityobjects()[obj])
        elif model.get_cityobjects()[obj].type == "Building":
            geometryTypes[obj] = "None"
            objectTypes[obj] = model.get_cityobjects()[obj].type
            totalHeights[obj] = getTotalHeight(model.get_cityobjects()[obj])
        else:
            geometryTypes[obj] = model.get_cityobjects()[obj].geometry[0].type
            objectTypes[obj] = model.get_cityobjects()[obj].type        

    modeldf["objectTypes"] = objectTypes
    modeldf["geometryTypes"] = geometryTypes
    modeldf["parents"] = parents
    modeldf["totalHeight"] = totalHeights
    
    surfacedf = {}
    
    for obj in cityObjIds:
        if model.get_cityobjects()[obj].type == "BuildingPart":
            for geometry in model.get_cityobjects()[obj].geometry:
                boundaryList = flattenSubBounds(geometry)
                for i in range(len(boundaryList)):
                    surfacedf["{}_{}".format(obj,i)] = {}
                    surfacedf["{}_{}".format(obj,i)]["parent"] = obj
                    curr_normal = getNormal(np.array(boundaryList[i]))
                    surfacedf["{}_{}".format(obj,i)]["normalX"] = curr_normal[0]
                    surfacedf["{}_{}".format(obj,i)]["normalY"] = curr_normal[1]
                    surfacedf["{}_{}".format(obj,i)]["normalZ"] = curr_normal[2]
                    surfacedf["{}_{}".format(obj,i)]["geometry"] = Polygon(boundaryList[i]).wkt
                    surfacedf["{}_{}".format(obj,i)]["semantic"] = geometry.surfaces[i]["type"]
                    if "attributes" in geometry.surfaces[i]:
                        surfacedf["{}_{}".format(obj,i)]["direction"] =  geometry.surfaces[i]["attributes"]["Direction"]
                        surfacedf["{}_{}".format(obj,i)]["slope"] = geometry.surfaces[i]["attributes"]["Slope"]
                    
                    else:
                        pass
        elif model.get_cityobjects()[obj].type != "Building" or model.get_cityobjects()[obj].type != "BuildingPart":
            for geometry in model.get_cityobjects()[obj].geometry:
                boundaryList = flattenSubBounds(geometry)
                for i in range(len(geometry.boundaries)):
                    surfacedf["{}_{}".format(obj,i)] = {}
                    surfacedf["{}_{}".format(obj,i)]["parent"] = obj
                    try:
                        surfacedf["{}_{}".format(obj,i)]["geometry"] = Polygon(boundaryList[i]).wkt                
                    except TypeError:
                        surfacedf["{}_{}".format(obj,i)]["geometry"] = Polygon(boundaryList[i]).wkt

    
    surfacedf = pd.DataFrame(surfacedf)
    surfacedf = surfacedf.transpose()
    namespace_manager = NamespaceManager(Graph())
    surfaceG = rpd.graph.to_graph(surfacedf, namespace_manager)
    modelG = rpd.graph.to_graph(modeldf, namespace_manager)
    surfaceTriples_t = list(surfaceG.triples((None,None,None)))
    modelTriples_t = list(modelG.triples((None,None,None)))
    modelTriples = []
    surfaceTriples = []
    for t in modelTriples_t:
        modelTriples.append([t[0].value, t[1].value, t[2].value])
    for s in surfaceTriples_t:
        surfaceTriples.append([s[0].value, s[1].value, s[2].value])
    del t,s
    
    parentRelations = []
    hasGeometryRels = []
    
    for s in surfaceTriples:
        if s[1] == "parent":
            parentRelations.append(s)
            
    for t in modelTriples:
        for s in parentRelations:
            if t[0] == s[2]:
                hasGeometryRels.append([t[0], "hasGeometry", s[0]])
                
    modelTriples = modelTriples + hasGeometryRels
    del t,s
    
    modelGraph = Graph(bind_namespaces="rdflib")
    surfaceGraph = Graph(bind_namespaces="rdflib")
    citygml = Namespace(CGML_URI)
    brep = Namespace(BREP_URI)
    sf = Namespace(SF_URI)
    ex = Namespace(EXA)
    modelGraph.bind("citygml", citygml)
    modelGraph.bind("sf", sf)
    modelGraph.bind("ex", ex)
    modelGraph.bind("csvw", CSVW)
    modelGraph.bind("geo", GEO)
    surfaceGraph.bind("citygml", citygml)
    surfaceGraph.bind("sf", sf)
    surfaceGraph.bind("ex", ex)
    surfaceGraph.bind("csvw", CSVW)
    surfaceGraph.bind("geo", GEO)
    surfaceGraph.bind("brep", brep)
    
    modelGraph.add((ex.CityModel, RDF.type, citygml.CityModel))
    modelGraph.add((ex.CityModel, citygml.extent, Literal(model.get_bbox())))
    
    scaleMat = np.eye(3)
    scaleMat = scaleMat * np.array(model.transform["scale"])
    translateMat = np.array(model.transform["translate"])
    transformationMatrix3x4 = np.hstack((scaleMat, translateMat.reshape((len(translateMat),1))))
    modelGraph.add((ex.CityModel, citygml.transformationMatrix, Literal(list(transformationMatrix3x4.flatten()))))
    
    for m in modelTriples:
        if m[1] == 'RelativeRidgeHeight' or m[1] == 'measuredHeight':
            modelGraph.add((ex.term(m[0]), citygml.measuredHeight, Literal(m[2])))
        elif m[1] == 'totalHeight':
            if m[2] == "None":
                modelGraph.add((ex.term(m[0]), citygml.height, CSVW.null))
            else:
                modelGraph.add((ex.term(m[0]), citygml.height, Literal(m[2])))
        elif m[1] == 'parents':
            modelGraph.add((ex.term(m[0]), citygml.parent, ex.term(m[2])))
        elif m[1] == 'roofType':
            modelGraph.add((ex.term(m[0]), citygml.roofType, Literal(m[2])))
        elif m[1] == "geometryTypes":
            if m[2] == 'None':
                modelGraph.add((ex.term(m[0]), citygml.GeometryType, CSVW.null))
            else:
                modelGraph.add((ex.term(m[0]), citygml.GeometryType, citygml.term(m[2][:4] + "Geometry")))
            if 'Solid' in m[2]:
                modelGraph.add((ex.term(m[0]), citygml.SolidType, citygml.term(m[2])))
        elif m[1] == "objectTypes":
            if m[2] == 'None':
                modelGraph.add((ex.term(m[0]), RDF.type, CSVW.null))
            else:
                modelGraph.add((ex.term(m[0]), RDF.type, citygml.term(m[2])))
        elif m[1] == "hasGeometry":
            modelGraph.add((ex.term(m[0]), GEO.hasGeometry, ex.term(m[2])))
    
    for s in surfaceTriples:
        if s[1] == "parent":
            surfaceGraph.add((ex.term(s[0]), citygml.parent, ex.term(s[2])))
        elif s[1] == "geometry":
            surfaceGraph.add((ex.term(s[0]), RDF.type, sf.Polygon))
            surfaceGraph.add((ex.term(s[0]), GEO.asWKT, Literal(s[2], datatype = GEO.wktLiteral)))
        elif s[1] == "semantic":
            if s[2] == 'None':
                surfaceGraph.add((ex.term(s[0]), RDF.type, CSVW.null))
            else:
                surfaceGraph.add((ex.term(s[0]), RDF.type, citygml.term(s[2]+"Type")))
        elif s[1] == "normalX":
            surfaceGraph.add((ex.term(s[0]), brep.directionNormalX, Literal(s[2], datatype = XSD.double)))
        elif s[1] == "normalY":
            surfaceGraph.add((ex.term(s[0]), brep.directionNormalY, Literal(s[2], datatype = XSD.double)))
        elif s[1] == "normalZ":
            surfaceGraph.add((ex.term(s[0]), brep.directionNormalZ, Literal(s[2], datatype = XSD.double)))
            
    
    resultGraph = modelGraph + surfaceGraph
    return resultGraph

if __name__ == "__main__":
    g = main("DenHaag_01.city.json")
    g.serialize("denhaag_rdf.json", format='json-ld')
