from cjio import cityjson
import tkinter as tk
from tkinter import filedialog, messagebox
import os
# Function to select a file using a file dialog 


# Path to your CityJSON file
file_path = filedialog.askopenfilename(
    title="Select CityJSON File",
    filetypes=(("CityJSON files", "*.json"), ("All files", "*.*"))
)

# Load the CityJSON file
cm = cityjson.load(file_path)

# Initialize counters
solid_surface_count = 0
multisurface_count = 0
solid_objects = 0
multisurface_objects = 0

# Iterate over all city objects
for co_id, co in cm.cityobjects.items():
    # Check if the city object has geometry
    for geom in co.geometry:
        if geom.type == "Solid":
            solid_objects += 1
            # Count surfaces in all shells
            for shell in geom.boundaries:
                surface_count = len(shell)
                solid_surface_count += surface_count
                print(f"CityObject {co_id} (Solid) has {surface_count} surfaces in this shell")
        elif geom.type == "MultiSurface":
            multisurface_objects += 1
            # MultiSurface boundaries are a list of surfaces directly
            surface_count = len(geom.boundaries)
            multisurface_count += surface_count
            print(f"CityObject {co_id} (MultiSurface) has {surface_count} surfaces")

# Calculate totals and averages
total_surface_count = solid_surface_count + multisurface_count
avg_solid_surfaces = solid_surface_count / solid_objects if solid_objects > 0 else 0
avg_multisurface_surfaces = multisurface_count / multisurface_objects if multisurface_objects > 0 else 0

# Generate table
table = f"""
Surface Boundary Counts:
| Geometry Type   | Objects | Total Surfaces | Avg Surfaces per Object |
|-----------------|---------|----------------|-------------------------|
| Solid           | {solid_objects:,}      | {solid_surface_count:,}       | {avg_solid_surfaces:.2f}        |
| MultiSurface    | {multisurface_objects:,}      | {multisurface_count:,}       | {avg_multisurface_surfaces:.2f} |
| Total           | {solid_objects + multisurface_objects:,}      | {total_surface_count:,}       | -                       |
"""
print(table)

# Detailed summary
print("Detailed Summary:")
print(f"- Solids: {solid_objects} objects with {solid_surface_count} total surfaces ({avg_solid_surfaces:.2f} avg per solid).")
print(f"- MultiSurfaces: {multisurface_objects} objects with {multisurface_count} total surfaces ({avg_multisurface_surfaces:.2f} avg per multisurface).")