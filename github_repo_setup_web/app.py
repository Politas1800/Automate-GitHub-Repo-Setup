from flask import Flask, render_template, request, jsonify
from github_repo_setup import (
    is_valid_github_url,
    download_repository,
    detect_python_version,
    search_python_files,
    setup_virtual_environment,
    install_dependencies,
    setup_git_hooks,
    check_tests_directory,
    run_tests
)
import os
import shutil
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Add a StreamHandler to also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
app.logger.addHandler(console_handler)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setup', methods=['POST'])
def setup_repository():
    app.logger.info("Received setup request")
    app.logger.info(f"Request form: {request.form}")
    app.logger.info(f"Request data: {request.data}")

    repo_url = request.form.get('repo_url')
    custom_path = request.form.get('custom_path', '')
    python_version = request.form.get('python_version', '')

    app.logger.info(f"Repo URL: {repo_url}")
    app.logger.info(f"Custom path: {custom_path}")
    app.logger.info(f"Python version: {python_version}")

    if not is_valid_github_url(repo_url):
        return jsonify({'error': 'Invalid GitHub URL'}), 400

    try:
        # Download repository
        local_repo_path = download_repository(repo_url, custom_path)

        # Detect Python version
        detected_version = detect_python_version(local_repo_path)
        if not python_version or python_version == "Detection failed":
            if detected_version:
                python_version = detected_version
            else:
                raise ValueError("Unable to detect Python version. Please specify a version manually.")

        # Setup virtual environment
        venv_path = setup_virtual_environment(local_repo_path, python_version)

        # Install dependencies
        install_dependencies(local_repo_path, venv_path)

        # Setup Git hooks
        setup_git_hooks(local_repo_path)

        # Check for tests and run them
        tests_dir = check_tests_directory(local_repo_path)
        test_results = run_tests(local_repo_path, venv_path) if tests_dir else None

        return jsonify({
            'success': True,
            'message': 'Repository setup completed successfully',
            'local_path': local_repo_path,
            'detected_version': detected_version,
            'used_version': python_version,
            'test_results': test_results
        })

    except Exception as e:
        app.logger.error(f"Error in setup_repository: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/detect_version', methods=['POST'])
def detect_version():
    repo_url = request.form.get('repo_url')
    app.logger.info(f"Received detect_version request for URL: {repo_url}")

    if not is_valid_github_url(repo_url):
        app.logger.warning(f"Invalid GitHub URL: {repo_url}")
        return jsonify({'error': 'Invalid GitHub URL'}), 400

    try:
        app.logger.info("Attempting to detect Python version")
        detected_version = detect_python_version(repo_url)
        app.logger.info(f"Detected Python version: {detected_version}")

        if detected_version:
            return jsonify({
                'success': True,
                'python_version': detected_version
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No Python version detected',
                'message': 'Unable to detect Python version from repository files'
            })

    except Exception as e:
        app.logger.error(f"Error in detect_version: {str(e)}")
        app.logger.exception("Full traceback:")
        return jsonify({
            'success': False,
            'error': 'Error detecting Python version',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
