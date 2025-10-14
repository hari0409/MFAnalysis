import os

def create_directory_structure(base_dir="fund_data", group=None):
    """Create directory structure for storing fund data.

    If `group` is provided, directories will be created under base_dir/group/...
    Returns a dict with 'holdings' and 'analysis' paths.
    """
    root = base_dir
    if group:
        root = os.path.join(base_dir, str(group))

    directories = {
        "holdings": os.path.join(root, "holdings"),
        "analysis": os.path.join(root, "analysis")
    }

    for dir_path in directories.values():
        os.makedirs(dir_path, exist_ok=True)

    return directories
