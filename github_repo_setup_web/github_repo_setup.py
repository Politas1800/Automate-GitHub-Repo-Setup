import os
import re
import subprocess
import logging
import requests
import base64
from github import Github
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Set up GitHub API authentication
github_token = os.getenv('GITHUB_TOKEN')
g = Github(github_token)

def print_colored(text, color):
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'reset': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")

def print_error(message):
    print_colored(f"Error: {message}", 'red')

def print_success(message):
    print_colored(message, 'green')

def print_warning(message):
    print_colored(message, 'yellow')

def print_info(message):
    print_colored(message, 'blue')

import logging

def is_valid_github_url(url):
    logging.debug(f"Validating URL: {url}, Type: {type(url)}")
    if url is None:
        logging.error("URL is None")
        return False
    if isinstance(url, bytes):
        try:
            url = url.decode('utf-8')
        except UnicodeDecodeError:
            logging.error("Failed to decode bytes to UTF-8")
            return False
    if not isinstance(url, str):
        logging.error(f"URL is not a string or bytes, but {type(url)}")
        return False
    try:
        parsed_url = urlparse(url)
        logging.debug(f"Parsed URL: {parsed_url}")
        result = all([
            parsed_url.scheme in ('http', 'https'),
            parsed_url.netloc == 'github.com',
            len(parsed_url.path.split('/')) >= 3
        ])
        logging.debug(f"URL validation result: {result}")
        return result
    except Exception as e:
        logging.error(f"Error parsing URL: {str(e)}")
        return False

def check_python_version(version):
    try:
        subprocess.run([f"python{version}", "--version"], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

def suggest_python_installation(version):
    print_warning(f"Python {version} is not installed on your system.")
    print_info("To install Python, you can:")
    print_info("1. Visit https://www.python.org/downloads/ and download the installer for your OS.")
    print_info("2. Use your system's package manager (e.g., apt for Ubuntu, brew for macOS).")
    print_info("3. Use pyenv to manage multiple Python versions: https://github.com/pyenv/pyenv")

def check_git_installed():
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False

def get_github_url():
    while True:
        url = input("Enter the GitHub repository URL: ").strip()
        if is_valid_github_url(url):
            return url
        print_error("Invalid GitHub URL. Please enter a valid URL (e.g., https://github.com/username/repo).")

def create_local_directory(repo_name, custom_path=None):
    if custom_path:
        base_dir = os.path.expanduser(custom_path)
    else:
        base_dir = os.path.expanduser("~/github_projects")
    try:
        os.makedirs(base_dir, exist_ok=True)
        local_dir = os.path.join(base_dir, repo_name)
        os.makedirs(local_dir, exist_ok=True)
        return local_dir
    except OSError as e:
        print_error(f"Failed to create directory: {e}")
        return None

def get_custom_path():
    while True:
        custom_path = input("Enter a custom path for repository download (leave blank for default): ").strip()
        if not custom_path:
            return None
        if os.path.isabs(custom_path):
            return custom_path
        print_error("Please enter an absolute path.")

def download_repository(url, custom_path=None):
    if not check_git_installed():
        print_error("Git is not installed. Please install Git and try again.")
        suggest_git_installation()
        sys.exit(1)

    repo_name = url.split("/")[-1].replace(".git", "")
    local_repo_path = create_local_directory(repo_name, custom_path)
    if not local_repo_path:
        print_error("Failed to create local directory. Exiting.")
        sys.exit(1)

    try:
        subprocess.run(["git", "clone", url, local_repo_path], check=True)
        print_success(f"Repository cloned successfully to {local_repo_path}")
        return local_repo_path
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to clone repository: {e}")
        sys.exit(1)

def suggest_git_installation():
    print_info("To install Git, you can:")
    print_info("1. Visit https://git-scm.com/downloads and download the installer for your OS.")
    print_info("2. Use your system's package manager (e.g., 'sudo apt install git' for Ubuntu, 'brew install git' for macOS).")

def search_python_files(directory):
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

import requests
import base64

def detect_python_version(repo_or_url):
    logging.info(f"Detecting Python version for: {repo_or_url}")
    if os.path.isdir(repo_or_url):
        return detect_local_python_version(repo_or_url)
    elif is_valid_github_url(repo_or_url):
        return detect_github_python_version(repo_or_url)
    else:
        logging.error(f"Invalid input: {repo_or_url}")
        return None

def detect_local_python_version(directory):
    version_files = ['.python-version', 'runtime.txt', 'pyproject.toml', 'setup.py']
    for file in version_files:
        file_path = os.path.join(directory, file)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read().strip()
                if file == '.python-version':
                    return content
                elif file == 'runtime.txt':
                    if content.startswith('python-'):
                        return content.split('-')[1].strip()
                elif file == 'pyproject.toml':
                    try:
                        data = toml.loads(content)
                        requires_python = data.get('project', {}).get('requires-python')
                        if requires_python:
                            match = re.search(r'>=(\d+\.\d+)', requires_python)
                            if match:
                                return match.group(1)
                    except Exception as e:
                        logging.warning(f"Error parsing pyproject.toml: {str(e)}")
                elif file == 'setup.py':
                    match = re.search(r'python_requires\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                    if match:
                        version_spec = match.group(1)
                        match = re.search(r'>=(\d+\.\d+)', version_spec)
                        if match:
                            return match.group(1)

    # Check shebang in Python files
    python_files = search_python_files(directory)
    for file in python_files[:5]:  # Check first 5 Python files
        with open(file, 'r') as f:
            first_line = f.readline().strip()
            if first_line.startswith('#!') and 'python' in first_line:
                version = first_line.split('python')[-1].strip()
                if version:
                    return version

    logging.warning("No Python version detected in local repository")
    return None

def detect_github_python_version(repo_url):
    logging.info(f"Detecting Python version for GitHub repository: {repo_url}")
    try:
        parts = repo_url.split('/')
        owner, repo = parts[-2], parts[-1].replace('.git', '')

        # Use the authenticated GitHub API
        repo = g.get_repo(f"{owner}/{repo}")

        version_files = ['.python-version', 'runtime.txt', 'pyproject.toml', 'setup.py', 'setup.cfg', 'tox.ini', 'Pipfile', 'requirements.txt']

        for file in version_files:
            try:
                content = repo.get_contents(file)
                decoded_content = content.decoded_content.decode('utf-8')
                logging.info(f"Content of {file}:\n{decoded_content}")

                if file == '.python-version':
                    version = decoded_content.strip()
                    logging.info(f"Detected version from .python-version: {version}")
                    return version
                elif file == 'runtime.txt':
                    match = re.search(r'python-(\d+\.\d+\.\d+)', decoded_content)
                    if match:
                        version = match.group(1)
                        logging.info(f"Detected version from runtime.txt: {version}")
                        return version
                elif file == 'pyproject.toml':
                    match = re.search(r'python\s*=\s*"([^"]+)"', decoded_content)
                    if match:
                        version = match.group(1)
                        logging.info(f"Detected version from pyproject.toml: {version}")
                        return version
                elif file == 'setup.py':
                    match = re.search(r'python_requires\s*=\s*[\'"]([^\'"]+)[\'"]', decoded_content)
                    if match:
                        version = match.group(1)
                        logging.info(f"Detected version from setup.py: {version}")
                        return version
                elif file == 'setup.cfg':
                    match = re.search(r'python_requires\s*=\s*([^\n]+)', decoded_content)
                    if match:
                        version = match.group(1)
                        logging.info(f"Detected version from setup.cfg: {version}")
                        return version
                elif file == 'tox.ini':
                    match = re.search(r'envlist\s*=\s*([^\n]+)', decoded_content)
                    if match:
                        versions = re.findall(r'py(\d+)', match.group(1))
                        if versions:
                            version = f"{versions[0][0]}.{versions[0][1]}"
                            logging.info(f"Detected version from tox.ini: {version}")
                            return version
                elif file == 'Pipfile':
                    match = re.search(r'python_version\s*=\s*[\'"]([^\'"]+)[\'"]', decoded_content)
                    if match:
                        version = match.group(1)
                        logging.info(f"Detected version from Pipfile: {version}")
                        return version
                elif file == 'requirements.txt':
                    match = re.search(r'python[>=]=(\d+\.\d+)', decoded_content)
                    if match:
                        version = match.group(1)
                        logging.info(f"Detected version from requirements.txt: {version}")
                        return version
            except Exception as e:
                logging.warning(f"Error parsing {file}: {str(e)}")

        # Check default branch for Python files
        try:
            contents = repo.get_contents("")
            python_files = [file for file in contents if file.name.endswith('.py')]
            if python_files:
                logging.info(f"Found Python files in the repository: {[file.name for file in python_files]}")
                return "3.6"  # Assume a minimum supported version if Python files are present
            else:
                logging.warning("No Python files found in the repository")

        except Exception as e:
            logging.warning(f"Error checking repository contents: {str(e)}")

        logging.warning("No Python version detected in GitHub repository")
        return None
    except Exception as e:
        logging.error(f"Error in detect_github_python_version: {str(e)}")
        return None

def recommend_python_version(directory):
    detected_version = detect_python_version(directory)
    if detected_version:
        print(f"Detected Python version: {detected_version}")
        user_choice = input(f"Would you like to use Python {detected_version} for the virtual environment? (y/n): ").lower()
        if user_choice == 'y':
            if check_python_version(detected_version):
                return detected_version
            else:
                print(f"Python {detected_version} is not available on your system.")
                suggest_python_installation(detected_version)
        elif user_choice == 'n':
            print("You've chosen to enter a custom Python version.")
        else:
            print("Invalid input. Defaulting to manual version entry.")
    else:
        print("No Python version detected in the project files.")

    while True:
        user_version = input("Please enter your desired Python version (e.g., 3.8): ")
        if re.match(r'^\d+\.\d+$', user_version):
            if check_python_version(user_version):
                return user_version
            else:
                print(f"Python {user_version} is not available on your system.")
                suggest_python_installation(user_version)
                print("Please install the desired Python version and try again.")
        else:
            print("Invalid version format. Please use the format 'X.Y' (e.g., 3.8).")

def setup_virtual_environment(repo_path, python_version):
    venv_path = os.path.join(repo_path, 'venv')

    # Extract the minimum Python version from the version string
    version_match = re.search(r'(\d+\.\d+)', python_version)
    if version_match:
        min_version = version_match.group(1)
    else:
        raise ValueError(f"Invalid Python version format: {python_version}")

    try:
        # Use the minimum version to create the virtual environment
        subprocess.run([f"python{min_version}", "-m", "venv", venv_path], check=True)
        print_success(f"Virtual environment created at {venv_path}")

        # Activate the virtual environment
        activate_script = os.path.join(venv_path, 'bin', 'activate')
        activate_command = f"source {activate_script}"

        # Update pip and install wheel
        subprocess.run(f"{activate_command} && pip install --upgrade pip wheel", shell=True, check=True)
        print_success("Pip upgraded and wheel installed in the virtual environment")

        return venv_path
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to set up virtual environment: {e}")
        suggest_python_installation(min_version)
        return None

def install_dependencies(venv_path, repo_path):
    requirements_file = os.path.join(repo_path, 'requirements.txt')
    pyproject_file = os.path.join(repo_path, 'pyproject.toml')

    if os.path.exists(requirements_file):
        print("Found requirements.txt. Installing dependencies...")
        pip_path = os.path.join(venv_path, 'bin', 'pip')
        try:
            subprocess.run([pip_path, 'install', '-r', requirements_file], check=True)
            print("Dependencies installed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            return False
    elif os.path.exists(pyproject_file):
        print("Found pyproject.toml. Installing dependencies using poetry...")
        poetry_path = os.path.join(venv_path, 'bin', 'poetry')
        try:
            subprocess.run(['pip', 'install', 'poetry'], check=True)  # Install poetry if not available
            subprocess.run([poetry_path, 'install'], cwd=repo_path, check=True)
            print("Dependencies installed successfully using poetry.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies with poetry: {e}")
            return False
    else:
        print("No requirements.txt or pyproject.toml found. Skipping dependency installation.")
        return True

def setup_git_hooks(repo_path):
    hooks_dir = os.path.join(repo_path, '.git', 'hooks')
    if not os.path.exists(hooks_dir):
        print("Git hooks directory not found. Skipping Git hooks setup.")
        return False

    pre_commit_hook = os.path.join(hooks_dir, 'pre-commit')
    with open(pre_commit_hook, 'w') as f:
        f.write("""#!/bin/sh
# Pre-commit hook to run tests before committing
python -m unittest discover tests
""")
    os.chmod(pre_commit_hook, 0o755)
    print("Git pre-commit hook set up successfully.")
    return True

def prompt_for_git_hooks():
    while True:
        choice = input("Do you want to set up Git hooks for this repository? (y/n): ").lower()
        if choice in ['y', 'n']:
            return choice == 'y'
        print("Invalid input. Please enter 'y' or 'n'.")

def open_readme(repo_path):
    readme_path = os.path.join(repo_path, 'README.md')
    if os.path.exists(readme_path):
        print(f"README.md found at {readme_path}")
        choice = input("Do you want to open README.md in your default text editor? (y/n): ").lower()
        if choice == 'y':
            try:
                if sys.platform == 'win32':
                    os.startfile(readme_path)
                elif sys.platform == 'darwin':
                    subprocess.run(['open', readme_path])
                else:
                    subprocess.run(['xdg-open', readme_path])
                print("README.md opened in default text editor.")
            except Exception as e:
                print(f"Error opening README.md: {e}")
        elif choice == 'n':
            print("Skipping README.md opening.")
        else:
            print("Invalid input. Skipping README.md opening.")
    else:
        print("No README.md found in the repository.")

def check_docker_compatibility(repo_path):
    docker_files = ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml']
    for file in docker_files:
        if os.path.exists(os.path.join(repo_path, file)):
            return True
    return False

def setup_docker_environment(repo_path):
    print("Setting up Docker environment...")
    try:
        subprocess.run(['docker', 'build', '-t', 'project-image', '.'], cwd=repo_path, check=True)
        print("Docker image built successfully.")
        subprocess.run(['docker', 'run', '-d', '--name', 'project-container', 'project-image'], cwd=repo_path, check=True)
        print("Docker container started successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error setting up Docker environment: {e}")
        return False

def check_tests_directory(repo_path):
    tests_dir = os.path.join(repo_path, 'tests')
    return os.path.isdir(tests_dir)

def run_tests(repo_path, venv_path):
    tests_dir = os.path.join(repo_path, 'tests')
    if not os.path.isdir(tests_dir):
        print("No tests directory found. Skipping test execution.")
        return False

    print("Running tests...")
    try:
        # Activate virtual environment and run tests
        activate_script = os.path.join(venv_path, 'bin', 'activate')
        test_command = f"source {activate_script} && python -m unittest discover {tests_dir}"
        result = subprocess.run(test_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("Tests executed successfully.")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running tests: {e}")
        print(e.stderr)
        return False

if __name__ == "__main__":
    try:
        print_info("GitHub Repository Setup Script")
        print_info("==============================")

        repo_url = get_github_url()
        custom_path = get_custom_path()
        local_repo_path = download_repository(repo_url, custom_path)
        print_success(f"Repository cloned to: {local_repo_path}")

        summary = {
            "repo_url": repo_url,
            "local_path": local_repo_path,
            "git_hooks": False,
            "readme_handled": False,
            "docker_compatibility": False,
            "venv_setup": False,
            "dependencies_installed": False,
            "tests_run": False,
            "python_version": None
        }

        if prompt_for_git_hooks():
            if setup_git_hooks(local_repo_path):
                print_success("Git hooks have been set up.")
                summary["git_hooks"] = True
            else:
                print_warning("Failed to set up Git hooks.")

        if open_readme(local_repo_path):
            summary["readme_handled"] = True

        if check_docker_compatibility(local_repo_path):
            print_info("Docker files detected in the repository.")
            summary["docker_compatibility"] = True
            choice = input("Do you want to set up the project using Docker? (y/n): ").lower()
            if choice == 'y':
                if setup_docker_environment(local_repo_path):
                    print_success("Docker environment set up successfully.")
                    print_success("Project setup completed successfully.")
                    summary["docker_setup"] = True
                else:
                    print_warning("Failed to set up Docker environment. Falling back to virtual environment setup.")
            elif choice != 'n':
                print_warning("Invalid input. Falling back to virtual environment setup.")

        python_files = search_python_files(local_repo_path)
        if python_files:
            print_info(f"Found {len(python_files)} Python file(s):")
            for file in python_files[:5]:  # Show only first 5 files
                print_info(f"  - {file}")
            if len(python_files) > 5:
                print_info(f"  ... and {len(python_files) - 5} more")

            recommended_version = recommend_python_version(local_repo_path)
            summary["python_version"] = recommended_version
            print_info(f"Recommended Python version: {recommended_version}")

            venv_path = setup_virtual_environment(local_repo_path, recommended_version)
            if venv_path:
                print_success("Virtual environment setup complete.")
                summary["venv_setup"] = True
                if install_dependencies(venv_path, local_repo_path):
                    print_success("Dependencies installed successfully.")
                    summary["dependencies_installed"] = True

                    if check_tests_directory(local_repo_path):
                        print_info("Tests directory detected.")
                        if run_tests(local_repo_path, venv_path):
                            print_success("All tests passed successfully.")
                        else:
                            print_warning("Some tests failed. Please review the test output above.")
                        summary["tests_run"] = True
                    else:
                        print_info("No tests directory found. Skipping test execution.")

                    print_success("Project setup completed successfully.")
                else:
                    print_warning("Project setup completed with errors in dependency installation.")
            else:
                print_error("Virtual environment setup failed. Please resolve the issues and try again.")
        else:
            print_warning("No Python files found in the repository.")
            print_info("Virtual environment setup and dependency installation skipped.")

    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
        print_error("Please try again or contact support if the issue persists.")

    print_info("\nSummary Report:")
    print_info("===============")
    print_info(f"Repository URL: {summary['repo_url']}")
    print_info(f"Local path: {summary['local_path']}")
    print_info(f"Git hooks setup: {'Successful' if summary['git_hooks'] else 'Not performed'}")
    print_info(f"README.md handling: {'Performed' if summary['readme_handled'] else 'Not performed'}")
    print_info(f"Docker compatibility: {'Detected' if summary['docker_compatibility'] else 'Not detected'}")
    if summary['docker_compatibility']:
        print_info(f"Docker setup: {'Successful' if summary.get('docker_setup', False) else 'Not performed'}")
    if summary['python_version']:
        print_info(f"Recommended Python version: {summary['python_version']}")
        print_info(f"Virtual environment setup: {'Successful' if summary['venv_setup'] else 'Failed'}")
        print_info(f"Dependencies installation: {'Successful' if summary['dependencies_installed'] else 'Failed or not performed'}")
        print_info(f"Automated testing: {'Performed' if summary['tests_run'] else 'Not performed'}")
    print_success("Project setup process completed.")
