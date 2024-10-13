def detect_python_version(directory):
    import os
    import toml

    version_files = ['.python-version', 'runtime.txt', 'pyproject.toml']
    for file in version_files:
        file_path = os.path.join(directory, file)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read().strip()
                if file == '.python-version':
                    return content
                elif file == 'runtime.txt':
                    if content.startswith('python-'):
                        return content.split('-')[1]
                elif file == 'pyproject.toml':
                    try:
                        data = toml.loads(content)
                        return data.get('tool', {}).get('poetry', {}).get('python')
                    except:
                        pass

    # Check shebang in Python files
    python_files = search_python_files(directory)
    for file in python_files[:5]:  # Check first 5 Python files
        with open(file, 'r') as f:
            first_line = f.readline().strip()
            if first_line.startswith('#!') and 'python' in first_line:
                version = first_line.split('python')[-1].strip()
                if version:
                    return version

    return None
