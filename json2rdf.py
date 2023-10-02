import json
from shapely.geometry import Polygon, Point, LineString
from rdflib import Graph, Literal, RDF, URIRef
from rdflib import Namespace
from rdflib.namespace import CSVW, DC, DCAT, DCTERMS, DOAP, FOAF, GEO, ODRL2, ORG, OWL, \
                           PROF, PROV, RDF, RDFS, SDO, SH, SKOS, SOSA, SSN, TIME, \
                           VOID, XMLNS, XSD
import numpy as np
                    
def flatten(matrix):
    flat_list = []
    for row in matrix:
        flat_list.extend(row)
    return flat_list
                
def dict2triples(data):
    initialList = []
    
    for key in data:
        initialList.append(["model","has", key])
        
    def recursive_items(dictionary):
        for key, value in dictionary.items():
            if type(value) is dict:
                yield (key, value)
                yield from recursive_items(value)
            else:
                yield (key, value)
    temp = []      
    for el in initialList:
        checkIfDict = data[el[2]]
        if type(checkIfDict) == dict:
            for key, value in recursive_items(checkIfDict):
                temp.append([el[2], key, value])
        else:
            temp.append([el[2],"is",checkIfDict])
    
    initialList = initialList + temp
    
    newTrples = []
    toRemove = []
    for i in range(len(initialList)):
        el = initialList[i]
        if "has" in el or "is" in el or "CityObjects" in el:
            pass
        else:
            toRemove.append(i)
            newTrples.append([el[0], "has", el[1]])
            newTrples.append([el[1], "is", el[2]])
            
    initialList = [i for j, i in enumerate(initialList) if j not in toRemove]
    initialList = initialList + newTrples
    
    del temp, newTrples, toRemove, i
    
    cityObjectIdxs = []
    for i in range(len(initialList)):
        el = initialList[i]
        if "CityObjects" in el and "has" not in el:
            cityObjectIdxs.append(i)
            
    initialList = [i for j, i in enumerate(initialList) if j not in cityObjectIdxs]

    cityObjectTrpls = []
    cityObjectIds = []
    for key in data:
        if key == "CityObjects":
            cityObjectIds = list(data[key].keys())
    
    for cid in cityObjectIds:
        cityObjectTrpls.append([cid, "typeof", "CityObjects"])
        for key, value in recursive_items(data["CityObjects"][cid]):
            cityObjectTrpls.append([cid, key, value])
    
    temp = []
    for tpl in cityObjectTrpls:
        if "geometry" in tpl[1]:
            for key, value in recursive_items(tpl[2][0]):
                temp.append([tpl[0], key, value])
    
    cityObjectTrpls = cityObjectTrpls + temp
    initialList = initialList + cityObjectTrpls
       
    vertices = [el for el in initialList if el[0] == "vertices" and el[1] == "is"][0][2]
    
    for el in initialList:
        if "boundaries" in el:
            for polyList in el[2]:
                temp = []
                for poly in polyList:
                    temp.append([tuple(vertices[poly[0][0]]), tuple(vertices[poly[0][1]]), tuple(vertices[poly[0][2]]), tuple(vertices[poly[0][3]]), tuple(vertices[poly[0][0]])])
                for t in temp:
                    el.append(Polygon(t).wkt)
                    
    toChangewktRecord = []
    for i in range(len(initialList)):
        if "boundaries" in initialList[i]:
            initialList[i][2] = [initialList[i][3:]]
            toChangewktRecord.append(i)
            
    for idx in toChangewktRecord:
        initialList[idx] = initialList[idx][:3]
    
    for el in initialList:
         if el[0] == "geographicalExtent":
             el[2] = Polygon([tuple(el[2][:2]), tuple(el[2][2:4]), tuple(el[2][4:]), tuple(el[2][:2])]).wkt
    return initialList
    
def triples2graph(initialList):
    
    rootSpace = "http://example.org/#"
    
    g = Graph(bind_namespaces="rdflib")
    CityGML_URI = "http://www.theworldavatar.com/ontology/ontocitygml/OntoCityGML.owl#"
    CityGML = URIRef(CityGML_URI)
    g.bind("citygml", CityGML)
    CityModel = URIRef(CityGML_URI+"CityModel")
    model = URIRef(rootSpace + 'model')
    g.add((model, RDF.type, CityModel))
    cityObjects = []
    cityObjIds = []
    for el in initialList:
        if el[2] == 'CityObjects' and el[1] == 'typeof':
            temp_obj = rootSpace + el[0]
            cityObjIds.append(el[0])
            cityObjects.append(temp_obj)
    
    cityObjectTripls = {}
    for i in range(len(cityObjIds)):
        cityObjectTripls[cityObjIds[i]]=[]
        for el in initialList:
            if el[0] == cityObjIds[i]:
                cityObjectTripls[cityObjIds[i]].append(el[1:])
    
    geoTypes = {}
    semTypes = {}
    lods = {}
    polygons = {}
    functions = {}
    for cid in cityObjIds:
        for el in cityObjectTripls[cid]:
            if el[0] == "type" and ("Solid" not in el[1]):
                semTypes[cid] = el[1][1:]
            if el[0] == "lod":
                lods[cid] = el[1]
            if el[0] == "type" and ("City" not in el[1]):
                geoTypes[cid] = el[1]
            if el[0] == "boundaries":
                polygons[cid] = el[1][0]
                
    for cid in cityObjIds:
        g.add((URIRef(rootSpace+cid), RDF.type, URIRef(CityGML_URI+semTypes[cid])))
        g.add((URIRef(rootSpace+cid), GEO.hasGeometry, URIRef(rootSpace+cid+"poly")))
        g.add((URIRef(rootSpace+cid+"poly"), RDF.type, URIRef(CityGML_URI+"lod{}{}".format(lods[cid], geoTypes[cid]))))
        g.add((URIRef(rootSpace+cid+"poly"), GEO.asWKT, Literal(polygons[cid], datatype = GEO.wktLiteral)))   
    
    scaleMat = np.eye(3)
    scale = []
    translate = []
    for el in initialList:
        if el[0] == "scale" and el[1] == "is":
            for i in el[2]:
                scale.append(i)
        if el[0] == "translate" and el[1] == "is":
            for j in el[2]:
                translate.append(j)
    scaleMat = scaleMat * np.array(scale)
    translate = np.array(translate)
    transformationMatrix3x4 = np.hstack((scaleMat, translate.reshape((len(translate),1))))
    extent, version, vertices = "", [], ""
    for el in initialList:
        if el[0] == "geographicalExtent" and el[1] == "is":
            extent = el[2]
        if el[0] == "vertices" and el[1] == "is":
            vertices = flatten(el[2])
        if el[0] == "version":
            version.append(el[2])
            
    g.add((model, URIRef(CityGML+"extent"), Literal(extent)))
    g.add((model, ODRL2.version, Literal(version[0])))
    for cityObject in cityObjects:
        g.add((model, OWL.oneOf, URIRef(cityObject)))
    g.add((model, URIRef(CityGML+"transformationMatrix"), Literal(list(transformationMatrix3x4.flatten()))))

    return g
        
if __name__ == "__main__":   
    with open("cube.city.json") as file:
        data = json.load(file)
    triples = dict2triples(data)
    graph = triples2graph(triples)
    print(graph.serialize(format='ttl'))



