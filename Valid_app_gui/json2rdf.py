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
    
def main(path):
    EXA = "http://example.org/#"
    CGML_URI = "http://www.theworldavatar.com/ontology/ontocitygml/OntoCityGML.owl#"
    SF_URI = "http://www.opengis.net/ont/sf#"
    BREP_URI = "https://github.com/OntoBREP/ontobrep/blob/master/owl/ontobrep.owl#"
    VALID_URI = "http://www.semanticweb.org/user/ontologies/2024/3/8/untitled-ontology-32#"

    path_ = clean_json_file(path, "cleaned_{}.json".format(str(datetime.now().timestamp())))
    model = cityjson.load(path_)
    modeldf = model.to_dataframe()
    
    cityObjIds = list(model.cityobjects.keys())
    # cityObjIds = [item.strip('{}') for item in cityObjIds_]
    # for id in cityObjIds:
    #     print(id)
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
            totalHeights[obj] = func.getTotalHeight(model.get_cityobjects()[obj])
        elif model.get_cityobjects()[obj].type == "Building":
            if model.get_cityobjects()[obj].attributes != {} :
                try:
                    geometryTypes[obj] = "lod" + model.get_cityobjects()[obj].geometry[0].lod + model.get_cityobjects()[obj].geometry[0].type
                except IndexError:
                    pass
            else:
                geometryTypes[obj] = "None"
            objectTypes[obj] = model.get_cityobjects()[obj].type
            totalHeights[obj] = func.getTotalHeight(model.get_cityobjects()[obj])
        else:
            geometryTypes[obj] = model.get_cityobjects()[obj].geometry[0].type
            objectTypes[obj] = model.get_cityobjects()[obj].type        

    modeldf["objectTypes"] = objectTypes
    modeldf["geometryTypes"] = geometryTypes
    modeldf["parents"] = parents
    modeldf["totalHeight"] = totalHeights
    
    surfacedf = {}
    
    for obj in cityObjIds:
        if model.get_cityobjects()[obj].type == "BuildingPart" or model.get_cityobjects()[obj].type == "Building":
            for geometry in model.get_cityobjects()[obj].geometry:
                if len(geometry.surfaces) != 0:
                    boundaryList = func.flattenSubBounds(geometry)
                    for i in range(len(boundaryList)):
                        surfacedf["{}_{}".format(obj,i)] = {}
                        surfacedf["{}_{}".format(obj,i)]["parent"] = obj
                        curr_normal = func.getNormal(np.array(boundaryList[i]))
                        surfacedf["{}_{}".format(obj,i)]["normalX"] = curr_normal[0]
                        surfacedf["{}_{}".format(obj,i)]["normalY"] = curr_normal[1]
                        surfacedf["{}_{}".format(obj,i)]["normalZ"] = curr_normal[2]
                        surfacedf["{}_{}".format(obj,i)]["geometry"] = Polygon(boundaryList[i]).wkt
                        try:
                            surfacedf["{}_{}".format(obj,i)]["semantic"] = geometry.surfaces[i]["type"]
                        except KeyError:
                            continue
                        surfacedf["{}_{}".format(obj,i)]["vertexCount_RL"] = func.vertexCount_RL(boundaryList[i])
                        surfacedf["{}_{}".format(obj,i)]["hasduplicatePoints_RL"] = func.hasduplicatePoints_RL(boundaryList[i])
                        surfacedf["{}_{}".format(obj,i)]["isClosed_RL"] = func.isClosed_RL(boundaryList[i])
                        surfacedf["{}_{}".format(obj,i)]["hasNoSelfIntersection_RL"] = func.hasNoSelfIntersection_RL(boundaryList[i])
                        surfacedf["{}_{}".format(obj,i)]["isCollapsedtoLine_RL"] = func.isCollapsedtoLine_RL(boundaryList[i])
                        surfacedf["{}_{}".format(obj,i)]["hasIntersectedRings_PL"] = func.hasIntersectedRings_PL(boundaryList[i])
                        surfacedf["{}_{}".format(obj,i)]["hasDuplicatedRings_PL"] = func.hasDuplicatedRings_PL(boundaryList[i])
                        surfacedf["{}_{}".format(obj,i)]["isCoplanar_PL"] = func.isCoplanar_PL(boundaryList[i])
                        try:
                            surfacedf["{}_{}".format(obj,i)]["isNormalDeviated_PL"] = func.isNormalDeviated_PL(boundaryList[i])
                        except ValueError:
                            surfacedf["{}_{}".format(obj,i)]["isNormalDeviated_PL"] = False
                        surfacedf["{}_{}".format(obj,i)]["hasInteriorDisconnected_PL"] = func.hasInteriorDisconnected_PL(boundaryList[i])
                        surfacedf["{}_{}".format(obj,i)]["hasHoleOutside_PL"] = func.hasHoleOutside_PL(boundaryList[i])
                        surfacedf["{}_{}".format(obj,i)]["hasInnerNestedRings_PL"] = func.hasInnerNestedRings_PL(boundaryList[i])
                        surfacedf["{}_{}".format(obj,i)]["isCcwise_PL"] = func.isCcwise_PL(boundaryList[i])
    
                        # if "attributes" in geometry.surfaces[i]:
                        #    surfacedf["{}_{}".format(obj,i)]["direction"] =  geometry.surfaces[i]["attributes"]["Direction"]
                        #    surfacedf["{}_{}".format(obj,i)]["slope"] = geometry.surfaces[i]["attributes"]["Slope"]
                        
                        # else:
                        #     pass

        else:
            for geometry in model.get_cityobjects()[obj].geometry:
                boundaryList = func.flattenSubBounds(geometry)
                for i in range(len(geometry.boundaries)):
                    surfacedf["{}_{}".format(obj,i)] = {}
                    surfacedf["{}_{}".format(obj,i)]["parent"] = obj
                    try:
                        surfacedf["{}_{}".format(obj,i)]["geometry"] = Polygon(boundaryList[i]).wkt                
                    except TypeError:
                        continue              
                    surfacedf["{}_{}".format(obj,i)]["vertexCount_RL"] = func.vertexCount_RL(boundaryList[i])
                    surfacedf["{}_{}".format(obj,i)]["hasduplicatePoints_RL"] = func.hasduplicatePoints_RL(boundaryList[i])
                    surfacedf["{}_{}".format(obj,i)]["isClosed_RL"] = func.isClosed_RL(boundaryList[i])
                    surfacedf["{}_{}".format(obj,i)]["hasNoSelfIntersection_RL"] = func.hasNoSelfIntersection_RL(boundaryList[i])
                    surfacedf["{}_{}".format(obj,i)]["isCollapsedtoLine_RL"] = func.isCollapsedtoLine_RL(boundaryList[i])
                    surfacedf["{}_{}".format(obj,i)]["hasIntersectedRings_PL"] = func.hasIntersectedRings_PL(boundaryList[i])
                    surfacedf["{}_{}".format(obj,i)]["hasDuplicatedRings_PL"] = func.hasDuplicatedRings_PL(boundaryList[i])
                    surfacedf["{}_{}".format(obj,i)]["isCoplanar_PL"] = func.isCoplanar_PL(boundaryList[i])
                    try:
                        surfacedf["{}_{}".format(obj,i)]["isNormalDeviated_PL"] = func.isNormalDeviated_PL(boundaryList[i])
                    except ValueError:
                        surfacedf["{}_{}".format(obj,i)]["isNormalDeviated_PL"] = False
                    surfacedf["{}_{}".format(obj,i)]["hasInteriorDisconnected_PL"] = func.hasInteriorDisconnected_PL(boundaryList[i])
                    surfacedf["{}_{}".format(obj,i)]["hasHoleOutside_PL"] = func.hasHoleOutside_PL(boundaryList[i])
                    surfacedf["{}_{}".format(obj,i)]["hasInnerNestedRings_PL"] = func.hasInnerNestedRings_PL(boundaryList[i])
                    surfacedf["{}_{}".format(obj,i)]["isCcwise_PL"] = func.isCcwise_PL(boundaryList[i])

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
    valid = Namespace(VALID_URI)
    modelGraph.bind("citygml", citygml)
    modelGraph.bind("sf", sf)
    modelGraph.bind("ex", ex)
    modelGraph.bind("csvw", CSVW)
    modelGraph.bind("geo", GEO)
    modelGraph.bind("valid", valid)
    surfaceGraph.bind("citygml", citygml)
    surfaceGraph.bind("sf", sf)
    surfaceGraph.bind("ex", ex)
    surfaceGraph.bind("csvw", CSVW)
    surfaceGraph.bind("geo", GEO)
    surfaceGraph.bind("brep", brep)
    surfaceGraph.bind("valid", valid)
    
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
                modelGraph.add((ex.term(m[0]), citygml.GeometryType, citygml.term(m[2])))
                if 'Solid' or 'MultiSurface' in m[2]:
                    modelGraph.add((ex.term(m[0]), RDF.type, citygml.SolidType))
                    # modelGraph.add((ex.term(m[0]), citygml.SolidType, citygml.term(m[2])))
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
            try:
                surfaceGraph.add((ex.term(s[2]), valid.groundSurfacePolygonNormals, Literal(func.groundSurfacePolygonNormals(surfacedf, s[2]), datatype = XSD.boolean)))
                surfaceGraph.add((ex.term(s[2]), valid.wallSurfacePolygonNormals, Literal(func.wallSurfacePolygonNormals(surfacedf, s[2]), datatype = XSD.boolean)))
                surfaceGraph.add((ex.term(s[2]), valid.roofSurfacePolygonNormals, Literal(func.roofSurfacePolygonNormals(surfacedf, s[2]), datatype = XSD.boolean)))
            except:
                ValueError            
        elif s[1] == "geometry":
            surfaceGraph.add((ex.term(s[0]), RDF.type, sf.Polygon))
            surfaceGraph.add((ex.term(s[0]), GEO.asWKT, Literal(s[2], datatype = GEO.wktLiteral)))
        elif s[1] == "semantic":
            if s[2] == 'None':
                surfaceGraph.add((ex.term(s[0]), RDF.type, CSVW.null))
            else:
                surfaceGraph.add((ex.term(s[0]), RDF.type, citygml.term(s[2]+"Type")))
                if s[2] == "GroundSurface":
                    surfaceGraph.add((ex.term(s[0]), valid.groundSurfaceNormals, Literal(func.groundSurfaceNormals(surfacedf, s[0]), datatype = XSD.boolean)))
                elif s[2] == "RoofSurface":
                    surfaceGraph.add((ex.term(s[0]), valid.roofSurfaceNormals, Literal(func.roofSurfaceNormals(surfacedf, s[0]), datatype = XSD.boolean)))
                elif s[2] == "WallSurface":
                    surfaceGraph.add((ex.term(s[0]), valid.wallSurfaceNormals, Literal(func.wallSurfaceNormals(surfacedf, s[0]), datatype = XSD.boolean)))
                elif s[2] == "OuterFloorSurface":
                    surfaceGraph.add((ex.term(s[0]), valid.outerFloorSurfaceNormals, Literal(func.outerFloorSurfaceNormals(surfacedf, s[0]), datatype = XSD.boolean)))
                elif s[2] == "OuterCeilingSurface":
                    surfaceGraph.add((ex.term(s[0]), valid.outerCeilingSurfaceNormals, Literal(func.outerCeilingSurfaceNormals(surfacedf, s[0]), datatype = XSD.boolean)))            
        
        elif s[1] == "normalX":
            surfaceGraph.add((ex.term(s[0]), brep.directionNormalX, Literal(s[2], datatype = XSD.double)))
        elif s[1] == "normalY":
            surfaceGraph.add((ex.term(s[0]), brep.directionNormalY, Literal(s[2], datatype = XSD.double)))
        elif s[1] == "normalZ":
            surfaceGraph.add((ex.term(s[0]), brep.directionNormalZ, Literal(s[2], datatype = XSD.double)))
            
    for obj in cityObjIds:
        objectInQuery = model.get_cityobjects()[obj]
        if len(objectInQuery.geometry) != 0 and objectInQuery.type != "TINRelief":
            modelGraph.add((ex.term(obj), valid.tooFewPolygons, Literal(func.tooFewPolygons_SL(objectInQuery), datatype = XSD.boolean)))
            modelGraph.add((ex.term(obj), valid.isWatertight, Literal(func.isWatertight_SL(objectInQuery), datatype = XSD.boolean)))
            modelGraph.add((ex.term(obj), valid.isVertexManifold, Literal(func.isVertexManifold_SL(objectInQuery), datatype = XSD.boolean)))
            modelGraph.add((ex.term(obj), valid.isEdgeManifold, Literal(func.isEdgeManifold_SL(objectInQuery), datatype = XSD.boolean)))
            modelGraph.add((ex.term(obj), valid.areAll3AnglesConnected, Literal(func.areAll3AnglesConnected_SL(objectInQuery), datatype = XSD.boolean)))
            modelGraph.add((ex.term(obj), valid.hasSelfIntersections, Literal(func.hasSelfIntersections_SL(objectInQuery), datatype = XSD.boolean)))
            modelGraph.add((ex.term(obj), valid.isCorrectOriented, Literal(func.isCorrectOriented_SL(objectInQuery), datatype = XSD.boolean)))
            modelGraph.add((ex.term(obj), valid.attributeHeightEqualsGeometry, Literal(func.attributeHeightEqualsGeometry(modelTriples, obj), datatype = XSD.boolean)))
            
    for s in surfaceTriples:
        if s[1] == "vertexCount_RL":
            surfaceGraph.add((ex.term(s[0]), valid.tooFewPoints, Literal(s[2], datatype = XSD.boolean)))
        elif s[1] == "hasduplicatePoints_RL":
            surfaceGraph.add((ex.term(s[0]), valid.consecutiveSamePoints, Literal(s[2], datatype = XSD.boolean)))
        elif s[1] == "isClosed_RL":
            surfaceGraph.add((ex.term(s[0]), valid.isClosed, Literal(s[2], datatype = XSD.boolean)))
        elif s[1] == "hasNoSelfIntersection_RL":
            surfaceGraph.add((ex.term(s[0]), valid.noSelfIntersection, Literal(s[2], datatype = XSD.boolean)))
        elif s[1] == "isCollapsedtoLine_RL":
            surfaceGraph.add((ex.term(s[0]), valid.isCollapsedtoLine, Literal(s[2], datatype = XSD.boolean)))
        elif s[1] == "hasIntersectedRings_PL":
            surfaceGraph.add((ex.term(s[0]), valid.hasIntersectedRings, Literal(s[2], datatype = XSD.boolean)))
        elif s[1] == "hasDuplicatedRings_PL":
            surfaceGraph.add((ex.term(s[0]), valid.hasDuplicatedRings, Literal(s[2], datatype = XSD.boolean)))
        elif s[1] == "isCoplanar_PL":
            surfaceGraph.add((ex.term(s[0]), valid.isCoplanar, Literal(s[2], datatype = XSD.boolean)))
        elif s[1] == "isNormalDeviated_PL":
            surfaceGraph.add((ex.term(s[0]), valid.isNormalsDeviated, Literal(s[2], datatype = XSD.boolean)))
        elif s[1] == "hasInteriorDisconnected_PL":
            surfaceGraph.add((ex.term(s[0]), valid.hasInteriorDisconnected, Literal(s[2], datatype = XSD.boolean)))
        elif s[1] == "hasHoleOutside_PL":
            surfaceGraph.add((ex.term(s[0]), valid.hasHoleOutside, Literal(s[2], datatype = XSD.boolean)))
        elif s[1] == "hasInnerNestedRings_PL":
            surfaceGraph.add((ex.term(s[0]), valid.hasInnerNestedRings, Literal(s[2], datatype = XSD.boolean)))
        elif s[1] == "isCcwise_PL":
            surfaceGraph.add((ex.term(s[0]), valid.isCcwise, Literal(s[2], datatype = XSD.boolean)))
    

    resultGraph = modelGraph + surfaceGraph
    return resultGraph

# if __name__ == "__main__":
#     g = main("Rotterdam.city.json")
#     g.serialize("rotterdam_rdf.ttl", format='ttl')
