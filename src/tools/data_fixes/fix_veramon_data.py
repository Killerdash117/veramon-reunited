import json
import os
import glob

# Convert catch rates and shiny rates back to decimals (from Pokemon-style rates)
def convert_to_proper_format(veramon_data):
    for veramon in veramon_data.values():
        # Convert catch_rate from Pokemon style (0-255) to decimal (0.0-1.0)
        if isinstance(veramon.get('catch_rate'), int):
            veramon['catch_rate'] = round(min(veramon['catch_rate'] / 255, 1.0), 2)
        
        # Convert shiny_rate from denominator to actual rate
        if isinstance(veramon.get('shiny_rate'), int) and veramon['shiny_rate'] > 1:
            veramon['shiny_rate'] = round(1 / veramon['shiny_rate'], 5)
        
        # Remove hidden_ability field if it exists
        if 'hidden_ability' in veramon:
            del veramon['hidden_ability']
        
        # If 'moves' exists, merge it into abilities
        if 'moves' in veramon:
            # Keep original abilities if they exist, otherwise use moves
            if 'abilities' not in veramon:
                veramon['abilities'] = veramon['moves']
            del veramon['moves']

# Find all veramon_data*.json files
data_files = glob.glob(os.path.join('src', 'data', 'veramon_data*.json'))

for file_path in data_files:
    print(f"Processing {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Skip the original veramon_data.json file
        if file_path.endswith('veramon_data.json'):
            print(f"Skipping original file: {file_path}")
            continue
            
        convert_to_proper_format(data)
        
        # Write the updated data back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        print(f"Successfully updated {file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

print("All files processed!")
