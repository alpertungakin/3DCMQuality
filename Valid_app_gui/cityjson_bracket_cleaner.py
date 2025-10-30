import json

def clean_keys_and_values(data):
    """
    Recursively traverse a JSON-like structure and clean both keys and values 
    by removing curly brackets '{}'.
    """
    if isinstance(data, dict):  # If the current item is a dictionary
        # Clean keys and values recursively
        return {
            clean_string(key): clean_keys_and_values(value)
            for key, value in data.items()
        }
    elif isinstance(data, list):  # If the current item is a list
        return [clean_keys_and_values(item) for item in data]
    elif isinstance(data, str):  # If the current item is a string
        return clean_string(data)
    else:  # For other types (e.g., int, float, bool), return as-is
        return data

def clean_string(s):
    """
    Clean a single string by removing curly brackets '{}' and surrounding spaces.
    """
    if isinstance(s, str):
        return s.replace('{', '').replace('}', '').strip()
    return s

def clean_json_file(input_path, output_path):
    """
    Clean all keys and values in a JSON file by removing curly brackets '{}' 
    and save the cleaned JSON to a new file.

    Args:
        input_path (str): Path to the input JSON file.
        output_path (str): Path to save the cleaned JSON file.
    """
    try:
        # Load the JSON file
        with open(input_path, 'r', encoding='utf-8') as file:
            json_data = json.load(file)

        # Clean all keys and values in the JSON data
        cleaned_data = clean_keys_and_values(json_data)

        # Save the cleaned JSON to a new file
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(cleaned_data, file, indent=4, ensure_ascii=False)

        print(f"JSON file cleaned and saved to: {output_path}")
    except Exception as e:
        print(f"Error processing JSON file: {e}")
    
    return output_path

# Example usage
if __name__ == "__main__":
    input_file_path = "Rotterdam.city.json"
    output_file_path = "cleaned_Rotterdam.city.json"
    clean_json_file(input_file_path, output_file_path)