import re
from collections import defaultdict

def extract_parent_node(focus_node):
    """Extract the parent node for subclasses like polygons, curves, or surfaces."""
    parts = focus_node.split('_')
    if len(parts) > 1 and parts[-1].isdigit():
        return '_'.join(parts[:-1])  # Remove the last numeric part to get the parent
    return focus_node  # Return original if no parent pattern detected

def parse_shacl_report(report_text):
    """Parse SHACL validation report and count unique focus nodes per source shape."""
    violation_pattern = re.compile(
        r'Source Shape: (.*?)\n\s*Focus Node: (.*?)\n',
        re.DOTALL
    )
    
    violations = defaultdict(set)
    total_violations = 0
    
    matches = violation_pattern.findall(report_text)
    for source_shape, focus_node in matches:
        total_violations += 1
        
        # Extract parent node if it's a Polygon, Curve, or Surface
        if any(keyword in source_shape for keyword in ["Polygon", "Curve", "Surface"]):
            parent_node = extract_parent_node(focus_node)
            violations[source_shape].add(parent_node)
        else:
            violations[source_shape].add(focus_node)
    
    return violations, total_violations

def print_summary(violations, total_violations):
    """Print the summary of unique affected nodes by source shape."""
    print(f"Total Violations: {total_violations}")
    print("\nSummary of Unique Affected Nodes by Source Shape:")
    print("-----------------------------------------------")
    for source_shape, affected_nodes in violations.items():
        print(f"Source Shape: {source_shape}")
        print(f"  Unique Affected Nodes: {len(affected_nodes)}")
        print()

# Read the validation report from a file
file_path = 'vienna_results.txt'  # Adjust this path to your file location
try:
    with open(file_path, 'r', encoding='utf-8') as file:
        report_text = file.read()
    
    # Process the report
    violations, total_violations = parse_shacl_report(report_text)
    print_summary(violations, total_violations)

except FileNotFoundError:
    print(f"Error: The file '{file_path}' was not found. Please check the file path.")
except Exception as e:
    print(f"An error occurred: {str(e)}")
