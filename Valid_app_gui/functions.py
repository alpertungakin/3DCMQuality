import numpy as np
from shapely.geometry import Polygon, LineString, MultiPoint, LinearRing, polygon
import shapely as shp
from skspatial.objects import Plane, Points, Vector, Triangle
import earcut as ec
import open3d as o3d
#from earcut_115 import earcut as ec115
from earcut_v2 import earcut as ec115
#from shapely.ops import triangulate

def getNormal(poly):
    #Newells method
    n = np.array([0.0, 0.0, 0.0])

    for i, v_curr in enumerate(poly):
        v_next = poly[(i+1) % len(poly),:]
        n[0] += (v_curr[1] - v_next[1]) * (v_curr[2] + v_next[2]) 
        n[1] += (v_curr[2] - v_next[2]) * (v_curr[0] + v_next[0])
        n[2] += (v_curr[0] - v_next[0]) * (v_curr[1] + v_next[1])

    norm = np.linalg.norm(n)
    if norm==0:
        normalised = np.array([0,0,0], dtype=np.float64)
    else:
        normalised = n/norm

    return list(normalised)

def getTotalHeight(objct):
    totalHeight = 0
    if objct.get_vertices() == []:
        totalHeight = "None"
    else:
        vertices = np.array(objct.get_vertices())
        h_list = list(vertices[:,2])
        totalHeight = max(h_list) - min(h_list)
    return totalHeight

def flattenSubBounds(geometry):
    bound_list = []
    if len(geometry.boundaries) == 1:
        for b in geometry.boundaries[0]:
            bound_list = bound_list + b
    else:
        for b in geometry.boundaries:
            bound_list = bound_list + b
    return bound_list

# Ring Level checks:
    
def closeRing_RL(bound_list):
    # ensure 103
    if abs(bound_list[0][0]-bound_list[-1][0])>0.01 and abs(bound_list[0][1]-bound_list[-1][1])>0.01 and abs(bound_list[0][2]-bound_list[-1][2])>0.01:
        bound_list.append(bound_list[0])
    else:
        pass
    return bound_list

def vertexCount_RL(bound_list):
    # check 101
    return len(bound_list) < 3

def hasduplicatePoints_RL(bound_list):
    # check 102
    temp = bound_list[:-1]
    haveDups = False
    for i in range(len(temp)-1):
        if abs(temp[i][0]-temp[i+1][0])<0.01 and abs(temp[i][1]-temp[i+1][1])<0.01 and abs(temp[i][2]-temp[i+1][2])<0.01:
            haveDups = True
        else:
            continue
    return haveDups

def isClosed_RL(bound_list):
    # check 103
    closeness = True
    if abs(bound_list[0][0]-bound_list[-1][0])>0.01 and abs(bound_list[0][1]-bound_list[-1][1])>0.01 and abs(bound_list[0][2]-bound_list[-1][2])>0.01:
        closeness = False
    return closeness

def makeHorizontal(bound_list):
    # before hasNoSelfIntersection_RL
    temp = []
    if Polygon(bound_list).area == 0:
        for v in bound_list:
            v_tuple = (v[1], v[2])
            temp.append(v_tuple)
    else:
        temp = bound_list
    return temp

def hasNoSelfIntersection_RL(bound_list):
    # check 104
    h = makeHorizontal(bound_list)
    issimple = Polygon(h).is_simple
    return issimple

def isCollapsedtoLine_RL(bound_list):
    # check 105
    h = makeHorizontal(bound_list)
    collapse = LineString(h).equals(LineString([h[0], h[-1]]))
    return collapse

# Polygon Level Checks:
def hasIntersectedRings_PL(bound_list):
    # check 201
    hasIntersectedRings = False
    rings = shp.get_rings(Polygon(makeHorizontal(bound_list))).tolist()
    if len(rings) > 1:
        temp = rings
        for i in range(len(rings)):
            temp.remove(rings[i])
            for j in range(len(temp)):
                if rings[i].intersect(temp[j]):
                    hasIntersectedRings = True
                    break
                else:
                    continue
    return hasIntersectedRings

def hasDuplicatedRings_PL(bound_list):
    # check 202
    hasDuplicatedRings = False
    rings = shp.get_rings(Polygon(makeHorizontal(bound_list))).tolist()
    if len(rings) > 1:
        temp = rings
        for i in range(len(rings)):
            temp.remove(rings[i])
            for j in range(len(temp)):
                if rings[i].equals_exact(temp[j], 0.01):
                    hasDuplicatedRings = True
                    break
                else:
                    continue
    return hasDuplicatedRings     
    
def isCoplanar_PL(bound_list):
    # check 203
    h = makeHorizontal(bound_list)
    planarity = Points(h).are_coplanar()
    return planarity

def isNormalDeviated_PL(bound_list):
    # check 204
    deviated = False
    h = makeHorizontal(bound_list)
    temp = ec.flatten([h])
    triangles = ec.earcut(temp['vertices'], temp['holes'], temp['dimensions'])
    normals = []
    for i in range(0, len(triangles), 3):
        normals.append(Triangle(h[triangles[i]], h[triangles[i+1]], h[triangles[i+2]]).normal())
    deviations = []
    try:
        for i in range(len(normals)):
            deviations.append(normals[i].angle_between(normals[i+1]))
    except:
        IndexError
    if max(deviations) > 0.1:
        deviated = True
    return deviated

def hasInteriorDisconnected_PL(bound_list):
    # check 205
    hasInteriorDisconnected = False
    exterior = shp.get_exterior_ring(Polygon(makeHorizontal(bound_list)))
    interiors = list(Polygon(makeHorizontal(bound_list)).interiors)
    for one in interiors:
        if shp.contains(exterior, one):
            if one.disjoint(exterior):
                hasInteriorDisconnected = True
    return hasInteriorDisconnected
    
def hasHoleOutside_PL(bound_list):
    # check 206
    hasHoleOutside = False
    exterior = shp.get_exterior_ring(Polygon(makeHorizontal(bound_list)))
    interiors = list(Polygon(makeHorizontal(bound_list)).interiors)
    for one in interiors:
        if shp.contains(exterior, one) == False:
            hasHoleOutside = True
    return hasHoleOutside
    
def hasInnerNestedRings_PL(bound_list):
    # check 207
    hasInnerNestedRings = False
    interiors = list(Polygon(makeHorizontal(bound_list)).interiors)
    if len(interiors) > 0:
        temp = interiors
        for i in range(len(interiors)):
            temp.remove(interiors[i])
            for j in range(len(temp)):
                if shp.contains(interiors[i],temp[j]):
                    hasInnerNestedRings = True
                    break
                else:
                    continue
    return hasInnerNestedRings
    
def isCcwise_PL(bound_list):
    # check 208
    isCcw = LinearRing(makeHorizontal(bound_list)).is_ccw
    return isCcw

# Shell level checks: .................
def triangulateFaces(bound_list):
    h = makeHorizontal(bound_list)
    temp = ec.flatten([h])
    triangles = ec.earcut(temp['vertices'], temp['holes'], temp['dimensions'])
    trianglesCluster = []
    for i in range(0, len(triangles), 3):
        trianglesCluster.append([triangles[i], triangles[i+1], triangles[i+2]])
    return np.array(trianglesCluster)

def getShellTriangles(cityObject):
    vertices = cityObject.get_vertices()
    boundaries = flattenSubBounds(cityObject.geometry[0])
    triangles = []
    for bound in boundaries:
        temp = triangulateFaces(bound)
        for t in temp:
            triangles.append([vertices.index(bound[t[0]]), vertices.index(bound[t[1]]), vertices.index(bound[t[2]])])
    return np.array(triangles)

def getShellTriangles_v2(cityObject):
    vertices = cityObject.get_vertices()
    boundaries = flattenSubBounds(cityObject.geometry[0])
    triangles = []
    for bound in boundaries:
        t = np.array(bound)
        shapelyPoly = Polygon(t)
        exterior_coords = list(shapelyPoly.exterior.coords)
        flat_coords = [coord for point in exterior_coords for coord in point]
        temp = ec115.earcut(flat_coords, None, 3)  # Triangulation
        temp_ = np.array(temp).reshape(-1, 3)
        for t in temp_:
            triangles.append([vertices.index(bound[t[0]]), vertices.index(bound[t[1]]), vertices.index(bound[t[2]])])
    return np.array(triangles)

def create3AngleMeshOfShell(cityObject):
   vertices = o3d.utility.Vector3dVector(np.array(cityObject.get_vertices()))
   triangles = o3d.utility.Vector3iVector(getShellTriangles_v2(cityObject))
   mesh_np = o3d.geometry.TriangleMesh(vertices, triangles)
   return mesh_np

def tooFewPolygons_SL(cityObject):
    # check 301
    hasTooFew = False
    mesh = create3AngleMeshOfShell(cityObject)
    count = len(mesh.triangles)
    if count < 4:
        hasTooFew = True
    return hasTooFew

def isWatertight_SL(cityObject):
    # check 302
    mesh = create3AngleMeshOfShell(cityObject)
    return mesh.is_watertight()

def isVertexManifold_SL(cityObject):
    # check 303
    mesh = create3AngleMeshOfShell(cityObject)
    return mesh.is_vertex_manifold()

def isEdgeManifold_SL(cityObject):
    # check 304
    mesh = create3AngleMeshOfShell(cityObject)
    return mesh.is_edge_manifold()  

def areAll3AnglesConnected_SL(cityObject):
    # check 305
    mesh = create3AngleMeshOfShell(cityObject)
    clusters = len(mesh.cluster_connected_triangles()[1])
    areConnected = True
    if clusters > 1:
        areConnected = False
    return areConnected

def hasSelfIntersections_SL(cityObject):
    # check 306
    mesh = create3AngleMeshOfShell(cityObject)
    return mesh.is_self_intersecting()
    
def isCorrectOriented_SL(cityObject):
    # check 307-308
    mesh = create3AngleMeshOfShell(cityObject)
    return mesh.is_orientable()

# Semantic checks:
def attributeHeightEqualsGeometry(modelTriples, ID):
    toCheck = []
    for t in modelTriples:
        if t[0] == ID:
            toCheck.append([t[1],t[2]])
    measured = 0
    attribute = 0
    for c in toCheck:
        if c[0] == 'RelativeRidgeHeight' or  c[0] == 'measuredHeight':
            measured = c[1]
        elif c[0] == 'totalHeight':
            attribute = c[1]
    return abs(measured - attribute) < 0.01
        
def storyHeightsEqualGeometry(modelTriples, ID):
    pass

def groundSurfaceNormals(surfacedf, ID):
    grounds = surfacedf[surfacedf["semantic"] == 'GroundSurface']
    thesurface = grounds.loc[ID]
    return thesurface["normalZ"] < 0

def roofSurfaceNormals(surfacedf, ID):
    roofs = surfacedf[surfacedf["semantic"] == 'RoofSurface']
    thesurface = roofs.loc[ID]
    return thesurface["normalZ"] > 0

def wallSurfaceNormals(surfacedf, ID):
    walls = surfacedf[surfacedf["semantic"] == 'WallSurface']
    thesurface = walls.loc[ID]
    return abs(thesurface["normalZ"]) < 0.02 #tan(1)

def outerFloorSurfaceNormals(surfacedf, ID):
    outerFloors = surfacedf[surfacedf["semantic"] == 'OuterFloorSurface']
    thesurface = outerFloors.loc[ID]
    return thesurface["normalZ"] > 0

def outerCeilingSurfaceNormals(surfacedf, ID):
    outerCeilings = surfacedf[surfacedf["semantic"] == 'OuterFloorSurface']
    thesurface = outerCeilings.loc[ID]
    return thesurface["normalZ"] < 0

def groundSurfacePolygonNormals(surfacedf, ID):
    siblings = surfacedf[surfacedf["parent"] == ID]
    groundSiblings = siblings[siblings["semantic"] == "GroundSurface"]
    directions = []
    for s in groundSiblings.iterrows():
        directions.append([s[1]["normalX"], s[1]["normalY"], s[1]["normalZ"]])
    angles = []
    check = 0
    if len(siblings) == 0:
        check = None
    if len(directions) == 1:
        check = Vector([0,0,-1]).angle_between(Vector(directions[0]))
    else:
        try:
            for i in range(len(directions)):
                angles.append(Vector(directions[i]).angle_between(Vector(directions[i+1])))
            check = abs(max(angles) - min(angles))
        except:
            IndexError
    return abs(check) < 5

def roofSurfacePolygonNormals(surfacedf, ID):
    siblings = surfacedf[surfacedf["parent"] == ID]
    roofSiblings = siblings[siblings["semantic"] == "RoofSurface"]
    directions = []
    for s in roofSiblings.iterrows():
        directions.append([s[1]["normalX"], s[1]["normalY"], s[1]["normalZ"]])
    angles = []
    check = 0
    if len(siblings) == 0:
        check = None
    if len(directions) == 1:
        check = Vector([0,0,1]).angle_between(Vector(directions[0]))
    else:
        try:
            for i in range(len(directions)):
                angles.append(Vector(directions[i]).angle_between(Vector(directions[i+1])))
            check = abs(max(angles) - min(angles))
        except:
            IndexError
    return abs(check) < 85  

def wallSurfacePolygonNormals(surfacedf, ID):
    siblings = surfacedf[surfacedf["parent"] == ID]
    wallSiblings = siblings[siblings["semantic"] == "WallSurface"]
    directions = []
    for s in wallSiblings.iterrows():
        directions.append([s[1]["normalX"], s[1]["normalY"], s[1]["normalZ"]])
    angles = []
    try:
        for i in range(len(directions)):
            angles.append(Vector(directions[i]).angle_between(Vector(directions[i+1])))
    except:
        IndexError        
    return abs(max(angles) - min(angles)) < 5  
    
    






