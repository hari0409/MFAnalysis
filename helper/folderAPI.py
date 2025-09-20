import os

def create_directory_structure(base_dir="fund_data"):
    """Create directory structure for storing fund data"""
    directories = {
        "holdings": os.path.join(base_dir, "holdings"),
        "analysis": os.path.join(base_dir, "analysis")
    }
    
    for dir_path in directories.values():
        os.makedirs(dir_path, exist_ok=True)
    
    return directories
