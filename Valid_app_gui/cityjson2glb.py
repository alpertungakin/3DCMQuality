import numpy as np
from cjio import cityjson
from shapely.geometry import Polygon
from pygltflib import GLTF2, Scene, Node, Mesh, Primitive, Buffer, BufferView, Accessor
from earcut_v2 import earcut as ec115
from typing import List, Tuple
import json
from glb_writer import GLBWriter
import pyproj

def cityjson_to_glb(city_objects: List[str], cm: cityjson.CityJSON, transformer, output_path: str):
    """Build the GLB and write it to disk. Returns the centroid (in the
    model's source CRS) that glb_writer used to recenter vertices, so callers
    can align an OSM basemap to the same point."""
    try:
        gltf, _, _, centroid = GLBWriter.create_glb(city_objects, cm, transformer)
        gltf.save_binary(output_path)
        print(f"GLB file saved to {output_path}")
        return centroid
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error converting CityJSON to GLB: {str(e)}")
        return None

if __name__ == "__main__":
    # Example usage

    temp_file_path = "data/cityjson/Lisboa_v3.json"
    cm = cityjson.load(temp_file_path)
    print(cm.get_epsg())
    transformer = pyproj.Transformer.from_crs(cm.get_epsg(), "EPSG:4978", always_xy=True)
    print(cm)
    output_path = "output_model.glb"
    
    city_objects = list(cm.get_cityobjects().keys())
    glb = cityjson_to_glb(city_objects, cm, transformer, output_path)