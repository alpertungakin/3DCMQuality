import json
from collections import defaultdict
from shapely.geometry import Polygon
from rdflib import Graph, Literal, RDF, URIRef
from rdflib import Namespace
from rdflib.namespace import NamespaceManager, CSVW, DC, DCAT, DCTERMS, DOAP, FOAF, GEO, ODRL2, ORG, OWL, \
                           PROF, PROV, RDF, RDFS, SDO, SH, SKOS, SOSA, SSN, TIME, \
                           VOID, XMLNS, XSD
import numpy as np
import pandas as pd
import cjio as cj
from cjio import cityjson
import functions as func
from cityjson_bracket_cleaner import clean_json_file
from datetime import datetime


def _is_missing(v):
    if v is None:
        return True
    if isinstance(v, float) and v != v:
        return True
    return False


def main(path):
    EXA = "http://example.org/#"
    CGML_URI = "http://www.theworldavatar.com/ontology/ontocitygml/OntoCityGML.owl#"
    SF_URI = "http://www.opengis.net/ont/sf#"
    BREP_URI = "https://github.com/OntoBREP/ontobrep/blob/master/owl/ontobrep.owl#"
    VALID_URI = "http://www.semanticweb.org/user/ontologies/2024/3/8/untitled-ontology-32#"

    path_ = clean_json_file(path, "cleaned_{}.json".format(str(datetime.now().timestamp())))
    model = cityjson.load(path_)
    modeldf = model.to_dataframe()

    cityobjects = model.cityobjects
    cityObjIds = list(cityobjects.keys())

    geometryTypes = {}
    objectTypes = {}
    parents = {}
    totalHeights = {}

    for obj in cityObjIds:
        co = cityobjects[obj]
        if len(co.parents) == 0:
            parents[obj] = "CityModel"
        else:
            parents[obj] = co.parents[0]
        co_type = co.type
        if co_type == "BuildingPart":
            geom0 = co.geometry[0]
            geometryTypes[obj] = "lod" + geom0.lod + geom0.type
            objectTypes[obj] = co_type
            totalHeights[obj] = func.getTotalHeight(co)
        elif co_type == "Building":
            if co.attributes != {}:
                try:
                    geom0 = co.geometry[0]
                    geometryTypes[obj] = "lod" + geom0.lod + geom0.type
                except IndexError:
                    pass
            else:
                geometryTypes[obj] = "None"
            objectTypes[obj] = co_type
            totalHeights[obj] = func.getTotalHeight(co)
        else:
            geometryTypes[obj] = co.geometry[0].type
            objectTypes[obj] = co_type

    modeldf["objectTypes"] = objectTypes
    modeldf["geometryTypes"] = geometryTypes
    modeldf["parents"] = parents
    modeldf["totalHeight"] = totalHeights

    surfacedf_dict = {}

    for obj in cityObjIds:
        co = cityobjects[obj]
        co_type = co.type
        if co_type == "BuildingPart" or co_type == "Building":
            for geometry in co.geometry:
                if len(geometry.surfaces) == 0:
                    continue
                boundaryList = func.flattenSubBounds(geometry)
                surfaces = geometry.surfaces
                for i in range(len(boundaryList)):
                    key = "{}_{}".format(obj, i)
                    bound_i = boundaryList[i]
                    entry = {"parent": obj}
                    curr_normal = func.getNormal(np.array(bound_i))
                    entry["normalX"] = curr_normal[0]
                    entry["normalY"] = curr_normal[1]
                    entry["normalZ"] = curr_normal[2]
                    entry["geometry"] = Polygon(bound_i).wkt
                    try:
                        entry["semantic"] = surfaces[i]["type"]
                    except KeyError:
                        surfacedf_dict[key] = entry
                        continue
                    entry["vertexCount_RL"] = func.vertexCount_RL(bound_i)
                    entry["hasduplicatePoints_RL"] = func.hasduplicatePoints_RL(bound_i)
                    entry["isClosed_RL"] = func.isClosed_RL(bound_i)
                    entry["hasNoSelfIntersection_RL"] = func.hasNoSelfIntersection_RL(bound_i)
                    entry["isCollapsedtoLine_RL"] = func.isCollapsedtoLine_RL(bound_i)
                    entry["hasIntersectedRings_PL"] = func.hasIntersectedRings_PL(bound_i)
                    entry["hasDuplicatedRings_PL"] = func.hasDuplicatedRings_PL(bound_i)
                    entry["isCoplanar_PL"] = func.isCoplanar_PL(bound_i)
                    try:
                        entry["isNormalDeviated_PL"] = func.isNormalDeviated_PL(bound_i)
                    except ValueError:
                        entry["isNormalDeviated_PL"] = False
                    entry["hasInteriorDisconnected_PL"] = func.hasInteriorDisconnected_PL(bound_i)
                    entry["hasHoleOutside_PL"] = func.hasHoleOutside_PL(bound_i)
                    entry["hasInnerNestedRings_PL"] = func.hasInnerNestedRings_PL(bound_i)
                    entry["isCcwise_PL"] = func.isCcwise_PL(bound_i)
                    surfacedf_dict[key] = entry
        else:
            for geometry in co.geometry:
                boundaryList = func.flattenSubBounds(geometry)
                for i in range(len(geometry.boundaries)):
                    key = "{}_{}".format(obj, i)
                    bound_i = boundaryList[i]
                    entry = {"parent": obj}
                    try:
                        entry["geometry"] = Polygon(bound_i).wkt
                    except TypeError:
                        surfacedf_dict[key] = entry
                        continue
                    entry["vertexCount_RL"] = func.vertexCount_RL(bound_i)
                    entry["hasduplicatePoints_RL"] = func.hasduplicatePoints_RL(bound_i)
                    entry["isClosed_RL"] = func.isClosed_RL(bound_i)
                    entry["hasNoSelfIntersection_RL"] = func.hasNoSelfIntersection_RL(bound_i)
                    entry["isCollapsedtoLine_RL"] = func.isCollapsedtoLine_RL(bound_i)
                    entry["hasIntersectedRings_PL"] = func.hasIntersectedRings_PL(bound_i)
                    entry["hasDuplicatedRings_PL"] = func.hasDuplicatedRings_PL(bound_i)
                    entry["isCoplanar_PL"] = func.isCoplanar_PL(bound_i)
                    try:
                        entry["isNormalDeviated_PL"] = func.isNormalDeviated_PL(bound_i)
                    except ValueError:
                        entry["isNormalDeviated_PL"] = False
                    entry["hasInteriorDisconnected_PL"] = func.hasInteriorDisconnected_PL(bound_i)
                    entry["hasHoleOutside_PL"] = func.hasHoleOutside_PL(bound_i)
                    entry["hasInnerNestedRings_PL"] = func.hasInnerNestedRings_PL(bound_i)
                    entry["isCcwise_PL"] = func.isCcwise_PL(bound_i)
                    surfacedf_dict[key] = entry

    # surfacedf is still produced because the per-parent normal helpers expect a DataFrame.
    surfacedf = pd.DataFrame(surfacedf_dict).transpose()

    # Flatten directly to (subject, predicate, value) lists — skip the rdfpandas
    # DataFrame→Graph→list round-trip entirely. NaN/None cells are dropped to match
    # rdfpandas' default behavior.
    modelTriples = []
    for subj_id, props in modeldf.to_dict(orient="index").items():
        for pred, val in props.items():
            if _is_missing(val):
                continue
            modelTriples.append([subj_id, pred, val])

    surfaceTriples = []
    for surf_id, props in surfacedf_dict.items():
        for pred, val in props.items():
            if val is None:
                continue
            surfaceTriples.append([surf_id, pred, val])

    # Indexed join replaces the original O(N_modelTriples × N_parentRelations) double loop.
    parent_rels_by_target = defaultdict(list)
    for s in surfaceTriples:
        if s[1] == "parent":
            parent_rels_by_target[s[2]].append(s)

    hasGeometryRels = []
    for t in modelTriples:
        rels = parent_rels_by_target.get(t[0])
        if rels:
            for s in rels:
                hasGeometryRels.append([t[0], "hasGeometry", s[0]])

    modelTriples = modelTriples + hasGeometryRels

    # Bucket modelTriples by subject so attributeHeightEqualsGeometry only scans
    # this object's triples instead of all of them.
    model_triples_by_subject = defaultdict(list)
    for t in modelTriples:
        model_triples_by_subject[t[0]].append(t)

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

    scaleMat = np.eye(3) * np.array(model.transform["scale"])
    translateMat = np.array(model.transform["translate"])
    transformationMatrix3x4 = np.hstack((scaleMat, translateMat.reshape((len(translateMat), 1))))
    modelGraph.add((ex.CityModel, citygml.transformationMatrix, Literal(list(transformationMatrix3x4.flatten()))))

    for m in modelTriples:
        p = m[1]
        if p == 'RelativeRidgeHeight' or p == 'measuredHeight':
            modelGraph.add((ex.term(m[0]), citygml.measuredHeight, Literal(m[2])))
        elif p == 'totalHeight':
            if m[2] == "None":
                modelGraph.add((ex.term(m[0]), citygml.height, CSVW.null))
            else:
                modelGraph.add((ex.term(m[0]), citygml.height, Literal(m[2])))
        elif p == 'parents':
            modelGraph.add((ex.term(m[0]), citygml.parent, ex.term(m[2])))
        elif p == 'roofType':
            modelGraph.add((ex.term(m[0]), citygml.roofType, Literal(m[2])))
        elif p == "geometryTypes":
            if m[2] == 'None':
                modelGraph.add((ex.term(m[0]), citygml.GeometryType, CSVW.null))
            else:
                modelGraph.add((ex.term(m[0]), citygml.GeometryType, citygml.term(m[2])))
                if 'Solid' or 'MultiSurface' in m[2]:
                    modelGraph.add((ex.term(m[0]), RDF.type, citygml.SolidType))
        elif p == "objectTypes":
            if m[2] == 'None':
                modelGraph.add((ex.term(m[0]), RDF.type, CSVW.null))
            else:
                modelGraph.add((ex.term(m[0]), RDF.type, citygml.term(m[2])))
        elif p == "hasGeometry":
            modelGraph.add((ex.term(m[0]), GEO.hasGeometry, ex.term(m[2])))

    # Pre-group by parent so each polygon-normal helper sees only its parent's rows;
    # combined with seen_parents this turns N_surface calls into N_parent calls.
    if "parent" in surfacedf.columns:
        parent_groups = {pid: gdf for pid, gdf in surfacedf.groupby("parent")}
    else:
        parent_groups = {}
    seen_parents = set()

    for s in surfaceTriples:
        p = s[1]
        if p == "parent":
            surfaceGraph.add((ex.term(s[0]), citygml.parent, ex.term(s[2])))
            if s[2] not in seen_parents:
                seen_parents.add(s[2])
                gdf = parent_groups.get(s[2], surfacedf)
                try:
                    surfaceGraph.add((ex.term(s[2]), valid.groundSurfacePolygonNormals, Literal(func.groundSurfacePolygonNormals(gdf, s[2]), datatype=XSD.boolean)))
                    surfaceGraph.add((ex.term(s[2]), valid.wallSurfacePolygonNormals, Literal(func.wallSurfacePolygonNormals(gdf, s[2]), datatype=XSD.boolean)))
                    surfaceGraph.add((ex.term(s[2]), valid.roofSurfacePolygonNormals, Literal(func.roofSurfacePolygonNormals(gdf, s[2]), datatype=XSD.boolean)))
                except Exception:
                    pass
        elif p == "geometry":
            surfaceGraph.add((ex.term(s[0]), RDF.type, sf.Polygon))
            surfaceGraph.add((ex.term(s[0]), GEO.asWKT, Literal(s[2], datatype=GEO.wktLiteral)))
        elif p == "semantic":
            if s[2] == 'None':
                surfaceGraph.add((ex.term(s[0]), RDF.type, CSVW.null))
            else:
                surfaceGraph.add((ex.term(s[0]), RDF.type, citygml.term(s[2] + "Type")))
                # Surface-level normal checks: the original helpers filter surfacedf
                # by semantic only to read this surface's normalZ — equivalent to a
                # direct dict lookup since we already computed it.
                nz = surfacedf_dict.get(s[0], {}).get("normalZ")
                if nz is not None:
                    sem = s[2]
                    if sem == "GroundSurface":
                        surfaceGraph.add((ex.term(s[0]), valid.groundSurfaceNormals, Literal(nz < 0, datatype=XSD.boolean)))
                    elif sem == "RoofSurface":
                        surfaceGraph.add((ex.term(s[0]), valid.roofSurfaceNormals, Literal(nz > 0, datatype=XSD.boolean)))
                    elif sem == "WallSurface":
                        surfaceGraph.add((ex.term(s[0]), valid.wallSurfaceNormals, Literal(abs(nz) < 0.02, datatype=XSD.boolean)))
                    elif sem == "OuterFloorSurface":
                        surfaceGraph.add((ex.term(s[0]), valid.outerFloorSurfaceNormals, Literal(nz > 0, datatype=XSD.boolean)))
                    elif sem == "OuterCeilingSurface":
                        # Mirrors functions.py outerCeilingSurfaceNormals: nz < 0.
                        surfaceGraph.add((ex.term(s[0]), valid.outerCeilingSurfaceNormals, Literal(nz < 0, datatype=XSD.boolean)))
        elif p == "normalX":
            surfaceGraph.add((ex.term(s[0]), brep.directionNormalX, Literal(s[2], datatype=XSD.double)))
        elif p == "normalY":
            surfaceGraph.add((ex.term(s[0]), brep.directionNormalY, Literal(s[2], datatype=XSD.double)))
        elif p == "normalZ":
            surfaceGraph.add((ex.term(s[0]), brep.directionNormalZ, Literal(s[2], datatype=XSD.double)))

    # Shell-level checks: build the open3d mesh once per object and reuse it for
    # all seven checks (each helper in functions.py rebuilt it from scratch).
    for obj in cityObjIds:
        objectInQuery = cityobjects[obj]
        if len(objectInQuery.geometry) != 0 and objectInQuery.type != "TINRelief":
            mesh = func.create3AngleMeshOfShell(objectInQuery)
            modelGraph.add((ex.term(obj), valid.tooFewPolygons, Literal(len(mesh.triangles) < 4, datatype=XSD.boolean)))
            modelGraph.add((ex.term(obj), valid.isWatertight, Literal(mesh.is_watertight(), datatype=XSD.boolean)))
            modelGraph.add((ex.term(obj), valid.isVertexManifold, Literal(mesh.is_vertex_manifold(), datatype=XSD.boolean)))
            modelGraph.add((ex.term(obj), valid.isEdgeManifold, Literal(mesh.is_edge_manifold(), datatype=XSD.boolean)))
            modelGraph.add((ex.term(obj), valid.areAll3AnglesConnected, Literal(len(mesh.cluster_connected_triangles()[1]) <= 1, datatype=XSD.boolean)))
            modelGraph.add((ex.term(obj), valid.hasSelfIntersections, Literal(mesh.is_self_intersecting(), datatype=XSD.boolean)))
            modelGraph.add((ex.term(obj), valid.isCorrectOriented, Literal(mesh.is_orientable(), datatype=XSD.boolean)))
            modelGraph.add((ex.term(obj), valid.attributeHeightEqualsGeometry, Literal(func.attributeHeightEqualsGeometry(model_triples_by_subject[obj], obj), datatype=XSD.boolean)))

    for s in surfaceTriples:
        p = s[1]
        if p == "vertexCount_RL":
            surfaceGraph.add((ex.term(s[0]), valid.tooFewPoints, Literal(s[2], datatype=XSD.boolean)))
        elif p == "hasduplicatePoints_RL":
            surfaceGraph.add((ex.term(s[0]), valid.consecutiveSamePoints, Literal(s[2], datatype=XSD.boolean)))
        elif p == "isClosed_RL":
            surfaceGraph.add((ex.term(s[0]), valid.isClosed, Literal(s[2], datatype=XSD.boolean)))
        elif p == "hasNoSelfIntersection_RL":
            surfaceGraph.add((ex.term(s[0]), valid.noSelfIntersection, Literal(s[2], datatype=XSD.boolean)))
        elif p == "isCollapsedtoLine_RL":
            surfaceGraph.add((ex.term(s[0]), valid.isCollapsedtoLine, Literal(s[2], datatype=XSD.boolean)))
        elif p == "hasIntersectedRings_PL":
            surfaceGraph.add((ex.term(s[0]), valid.hasIntersectedRings, Literal(s[2], datatype=XSD.boolean)))
        elif p == "hasDuplicatedRings_PL":
            surfaceGraph.add((ex.term(s[0]), valid.hasDuplicatedRings, Literal(s[2], datatype=XSD.boolean)))
        elif p == "isCoplanar_PL":
            surfaceGraph.add((ex.term(s[0]), valid.isCoplanar, Literal(s[2], datatype=XSD.boolean)))
        elif p == "isNormalDeviated_PL":
            surfaceGraph.add((ex.term(s[0]), valid.isNormalsDeviated, Literal(s[2], datatype=XSD.boolean)))
        elif p == "hasInteriorDisconnected_PL":
            surfaceGraph.add((ex.term(s[0]), valid.hasInteriorDisconnected, Literal(s[2], datatype=XSD.boolean)))
        elif p == "hasHoleOutside_PL":
            surfaceGraph.add((ex.term(s[0]), valid.hasHoleOutside, Literal(s[2], datatype=XSD.boolean)))
        elif p == "hasInnerNestedRings_PL":
            surfaceGraph.add((ex.term(s[0]), valid.hasInnerNestedRings, Literal(s[2], datatype=XSD.boolean)))
        elif p == "isCcwise_PL":
            surfaceGraph.add((ex.term(s[0]), valid.isCcwise, Literal(s[2], datatype=XSD.boolean)))

    resultGraph = modelGraph + surfaceGraph
    return resultGraph

# if __name__ == "__main__":
#     g = main("Rotterdam.city.json")
#     g.serialize("rotterdam_rdf.ttl", format='ttl')
