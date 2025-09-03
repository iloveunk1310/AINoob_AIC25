import json
import os
import math
import glob
from collections import defaultdict

# Color name to RGB mapping (common colors)
color_to_rgb = {
    'red': [255, 0, 0],
    'green': [0, 255, 0], 
    'blue': [0, 0, 255],
    'yellow': [255, 255, 0],
    'cyan': [0, 255, 255],
    'magenta': [255, 0, 255],
    'orange': [255, 165, 0],
    'purple': [128, 0, 128],
    'pink': [255, 192, 203],
    'brown': [165, 42, 42],
    'gray': [128, 128, 128],
    'grey': [128, 128, 128],
    'black': [0, 0, 0],
    'white': [255, 255, 255],
    'lime': [0, 255, 0],
    'navy': [0, 0, 128],
    'teal': [0, 128, 128],
    'olive': [128, 128, 0],
    'maroon': [128, 0, 0],
    'silver': [192, 192, 192],
    'gold': [255, 215, 0]
}

def rgb_to_color_name(rgb):

    min_distance = float('inf')
    closest_color = 'unknown'
    
    for color_name, color_rgb in color_to_rgb.items():
        distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(rgb, color_rgb)))
        if distance < min_distance:
            min_distance = distance
            closest_color = color_name
    
    return closest_color

def calculate_color_similarity(color1, color2):

    # Get RGB values for both colors
    rgb1 = color_to_rgb.get(color1.lower(), [0, 0, 0])
    rgb2 = color_to_rgb.get(color2.lower(), [0, 0, 0])
    
    # Calculate Euclidean distance in RGB space
    distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)))
    
    # Maximum possible distance in RGB space is sqrt(255^2 + 255^2 + 255^2) ≈ 441.67
    max_distance = math.sqrt(255**2 + 255**2 + 255**2)
    
    # Convert distance to similarity (0-1 scale)
    similarity = 1.0 - (distance / max_distance)
    
    return max(0.0, similarity)  # Ensure non-negative

def calculate_enhanced_similarity(dict1, dict2, dict2_rgb):

    if not dict1 or not dict2:
        return 0.0, []
    
    matches = 0
    total_comparisons = 0
    color_similarities = []
    
    # Check each object in user_dict against JSON data
    for user_obj, user_color in dict1.items():
        user_obj_lower = user_obj.lower()
        
        # Find exact match
        if user_obj_lower in dict2 and dict2[user_obj_lower] == user_color:
            matches += 1
            total_comparisons += 1
            color_similarities.append(1.0)  # Perfect match
        # Check for partial matches (object exists but different color)
        elif user_obj_lower in dict2:
            json_color = dict2[user_obj_lower]
            color_sim = calculate_color_similarity(user_color, json_color)
            # Weight the match based on color similarity
            weighted_match = color_sim * 0.8  # 80% weight for color similarity
            matches += weighted_match
            total_comparisons += 1
            color_similarities.append(color_sim)
        # Object doesn't exist in JSON
        else:
            total_comparisons += 1
            color_similarities.append(0.0)
    
    # Check for objects in JSON that match user_dict colors
    for json_obj, json_color in dict2.items():
        if json_obj not in [obj.lower() for obj in dict1.keys()]:
            # Check if this color exists in user_dict
            if json_color in dict1.values():
                # Partial credit for color match
                matches += 0.3
                total_comparisons += 0.3
    
    return matches / total_comparisons if total_comparisons > 0 else 0.0, color_similarities

def process_json_file(file_path):

    try:
        with open(file_path, 'r') as f:
            json_data = json.load(f)
    except FileNotFoundError:
        print(f"Warning: Could not find file at {file_path}")
        return {}, {}
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON in file {file_path}")
        return {}, {}
    
    # Extract object-color mappings from JSON with RGB data
    json_object_colors = {}
    json_object_rgb = {}
    object_color_counts = defaultdict(lambda: defaultdict(int))
    object_rgb_data = defaultdict(list)
    
    for entry in json_data['entries']:
        obj_class = entry['class'].lower()
        color_name = entry['dominant_name']
        rgb_values = entry['dominant_rgb']
        score = entry['score']
        
        # Store RGB data for each object
        object_rgb_data[obj_class].append({
            'rgb': rgb_values,
            'color_name': color_name,
            'score': score
        })
        
        # Count occurrences weighted by detection score
        object_color_counts[obj_class][color_name] += score
    
    # Get the most common color for each object (weighted by score)
    for obj_class, color_counts in object_color_counts.items():
        if color_counts:
            most_common_color = max(color_counts.items(), key=lambda x: x[1])[0]
            json_object_colors[obj_class] = most_common_color
            
            # Get the RGB values for the most common color
            rgb_data = object_rgb_data[obj_class]
            most_common_entry = max(rgb_data, key=lambda x: x['score'])
            json_object_rgb[obj_class] = most_common_entry['rgb']
    
    return json_object_colors, json_object_rgb

def calculate_similarity_scores_dict(user_dict, object_colors_dir="object_colors", verbose=False):

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    object_colors_path = os.path.join(script_dir, object_colors_dir)
    
    # Check if directory exists
    if not os.path.exists(object_colors_path):
        print(f"Error: Directory '{object_colors_dir}' not found at {object_colors_path}")
        return {}
    
    # Find all JSON files in the directory
    json_files = glob.glob(os.path.join(object_colors_path, "*.colors.json"))
    
    if not json_files:
        print(f"No .colors.json files found in {object_colors_path}")
        return {}
    
    similarity_scores_dict = {}
    
    if verbose:
        print(f"Found {len(json_files)} JSON files in {object_colors_dir}/")
        print(f"User dictionary: {user_dict}")
        print("=" * 60)
    
    for file_path in sorted(json_files):
        # Extract file name without extension for the key
        file_name = os.path.basename(file_path)
        file_key = file_name.replace('.json', '')  # Remove .json extension
        
        if verbose:
            print(f"\nProcessing file: {file_name}")
        
        # Process the JSON file
        json_object_colors, json_object_rgb = process_json_file(file_path)
        
        if not json_object_colors:
            # File not found or invalid, assign 0 score
            similarity_scores_dict[file_key] = 0.0
            if verbose:
                print(f"  Score: 0.000 (0.0%) - File not found or invalid")
            continue
        
        # Calculate similarity
        similarity_score, color_similarities = calculate_enhanced_similarity(
            user_dict, json_object_colors, json_object_rgb
        )
        
        similarity_scores_dict[file_key] = similarity_score
        
        if verbose:
            print(f"  Score: {similarity_score:.3f} ({similarity_score*100:.1f}%)")
            
            # Show object mappings
            print(f"  JSON objects: {list(json_object_colors.keys())}")
            print(f"  JSON colors: {list(set(json_object_colors.values()))}")
            
            # Show detailed analysis for each object
            for i, (user_obj, user_color) in enumerate(user_dict.items()):
                user_obj_lower = user_obj.lower()
                if user_obj_lower in json_object_colors:
                    json_color = json_object_colors[user_obj_lower]
                    if json_color == user_color:
                        print(f"    ✓ {user_obj}: {user_color} - EXACT MATCH")
                    else:
                        color_sim = color_similarities[i] if i < len(color_similarities) else 0.0
                        print(f"    ✗ {user_obj}: {user_color} vs {json_color} - Color similarity: {color_sim:.3f}")
                else:
                    print(f"    ? {user_obj}: {user_color} - NOT FOUND")
    
    return similarity_scores_dict

# Example usage and testing
if __name__ == "__main__":
    # Example user dictionary
    user_dict = {'skyscraper': 'red', 'lantern': 'red'}
    
    print("=== SIMILARITY SCORE CALCULATION ===")
    print(f"User dictionary: {user_dict}")
    print(f"Processing all files in object_colors/ directory")
    
    # Calculate scores with verbose output
    scores_dict = calculate_similarity_scores_dict(user_dict, verbose=True)
    
    print(f"\n=== FINAL RESULTS ===")
    print(f"Similarity scores dictionary:")
    for file_name, score in scores_dict.items():
        print(f"  {file_name}: {score:.3f} ({score*100:.1f}%)")
    
    # Example usage as a function
    def get_scores_for_directory(user_dict, directory="object_colors"):
        """Helper function to get scores for all files in a directory"""
        return calculate_similarity_scores_dict(user_dict, directory)
    
    # Example:
    # my_dict = {'car': 'blue', 'tree': 'green'}
    # results = get_scores_for_directory(my_dict)
    # print(f"Scores: {results}")
    # # Output: {'001.colors': 0.456, '002.colors': 0.789, ...}