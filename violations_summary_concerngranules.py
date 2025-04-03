from collections import defaultdict
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import os

# Sample validation report (replace with full text if needed)
file_path = filedialog.askopenfilename(
    title="Select Validation Report",
    filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
)
with open(file_path, 'r', encoding='utf-8') as file:
    validation_report = file.read()

# Placeholder total (replace with actual value)
TOTAL_SOLIDS = input("Enter the total number of solids: ")
TOTAL_SURFACES = input("Enter the total number of surfaces: ")
try:
    TOTAL_SOLIDS = int(TOTAL_SOLIDS)
    TOTAL_SURFACES = int(TOTAL_SURFACES)
except ValueError:
    print("Invalid input for total solids. Please enter a valid integer.")
    TOTAL_SOLIDS = 0
    TOTAL_SURFACES = 0

# Parse the report
lines = validation_report.splitlines()
solid_violations = set()  # Unique focus nodes for solids with citygml:SolidType- violations
semantic_violations = set()  # Unique focus nodes for semantic violations

for i, line in enumerate(lines):
    if "Focus Node:" in line:
        focus_node = line.split("Focus Node: ")[1].strip()
        # Look back to find the Source Shape
        for j in range(i - 1, -1, -1):
            if "Source Shape:" in lines[j]:
                source_shape = lines[j].split("Source Shape: ")[1].strip()
                # Only include citygml:SolidType- violations, exclude citygml:SolidType-exterior
                if "citygml:SolidType-" in source_shape and "citygml:SolidType-exterior" not in source_shape:
                    solid_violations.add(focus_node)
                # Check for semantic violations
                elif "SurfaceType" in source_shape:
                    semantic_violations.add(focus_node)
                break

# Calculate stats
solid_count = len(solid_violations)
semantic_count = len(semantic_violations)
solid_pct = (solid_count / TOTAL_SOLIDS) * 100 if TOTAL_SOLIDS > 0 else 0
semantic_pct = (semantic_count / TOTAL_SURFACES) * 100 if TOTAL_SURFACES > 0 else 0

# Generate table
table = f"""
Granularity-Based Validation Results (Solids Only):
| Level  | Total Instances | Violations | Percentage |
|--------|-----------------|------------|------------|
| Solids | {TOTAL_SOLIDS:,}             | {solid_count:,}     | {solid_pct:.2f}%    |
| Surfaces | {TOTAL_SURFACES:,}           | {semantic_count:,}     | {semantic_pct:.2f}%    |
"""
print(table)

# Detailed output
print("Detailed Breakdown:")
print(f"- Solids: {solid_count} unique solids failed citygml:SolidType- checks (excluding exterior) out of {TOTAL_SOLIDS} ({solid_pct:.2f}%).")