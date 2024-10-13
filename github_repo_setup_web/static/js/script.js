console.log('Script loaded');

document.addEventListener('DOMContentLoaded', (event) => {
    console.log('DOM fully loaded and parsed');

    const form = document.getElementById('setup-form');
    const repoUrlInput = document.getElementById('repo-url');
    const pythonVersionInput = document.getElementById('python-version');
    const customPythonVersionInput = document.getElementById('custom-python-version');
    const loadingDiv = document.getElementById('loading');
    const resultDiv = document.getElementById('result');
    const resultMessage = document.getElementById('result-message');
    const resultDetails = document.getElementById('result-details');

    console.log('Form elements:', {
        form: form,
        repoUrlInput: repoUrlInput,
        pythonVersionInput: pythonVersionInput,
        customPythonVersionInput: customPythonVersionInput,
        loadingDiv: loadingDiv,
        resultDiv: resultDiv,
        resultMessage: resultMessage,
        resultDetails: resultDetails
    });

    function showLoading(message = 'Loading...') {
        console.log('Showing loading:', message);
        loadingDiv.classList.remove('hidden');
        loadingDiv.querySelector('p').textContent = message;
        document.body.style.cursor = 'wait';
        const spinner = loadingDiv.querySelector('.spinner');
        spinner.style.animation = 'spin 1s linear infinite';
    }

    function hideLoading() {
        console.log('Hiding loading');
        loadingDiv.classList.add('hidden');
        document.body.style.cursor = 'default';
        const spinner = loadingDiv.querySelector('.spinner');
        spinner.style.animation = 'none';
    }

    function showError(message) {
        console.error('Error:', message);
        resultMessage.textContent = 'Error: ' + message;
        resultMessage.classList.add('error');
        resultDiv.classList.remove('hidden');
        resultDiv.scrollIntoView({ behavior: 'smooth' });
        setTimeout(() => {
            resultMessage.classList.add('shake');
            setTimeout(() => resultMessage.classList.remove('shake'), 500);
        }, 100);
    }

    function showSuccess(data) {
        console.log('Showing success:', data);
        resultMessage.textContent = data.message || 'Setup completed successfully';
        resultMessage.classList.remove('error');
        resultDetails.innerHTML = '';
        if (data.details) {
            data.details.forEach(detail => {
                const li = document.createElement('li');
                li.textContent = detail;
                resultDetails.appendChild(li);
            });
        }
        resultDiv.classList.remove('hidden');
    }

    function isValidGitHubUrl(url) {
        const githubUrlRegex = /^https?:\/\/(www\.)?github\.com\/[\w-]+\/[\w.-]+$/;
        return githubUrlRegex.test(url);
    }

    function validateGitHubUrl() {
        const repoUrl = repoUrlInput.value.trim();
        if (repoUrl) {
            if (isValidGitHubUrl(repoUrl)) {
                repoUrlInput.classList.remove('invalid');
                repoUrlInput.classList.add('valid');
                return true;
            } else {
                repoUrlInput.classList.remove('valid');
                repoUrlInput.classList.add('invalid');
                showError('Invalid GitHub URL. Please enter a valid URL.');
                return false;
            }
        } else {
            repoUrlInput.classList.remove('valid', 'invalid');
            resultDiv.classList.add('hidden');
            return false;
        }
    }

function detectPythonVersion(repoUrl) {
    console.log('Detecting Python version for:', repoUrl);
    pythonVersionInput.value = 'Detecting...';
    customPythonVersionInput.value = '';
    showLoading('Detecting Python version...');

    const formData = new FormData();
    formData.append('repo_url', repoUrl);

    console.log('Form data:', Object.fromEntries(formData));

    fetch('/detect_version', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);
        return response.text().then(text => {
            console.log('Raw response:', text);
            try {
                return JSON.parse(text);
            } catch (error) {
                console.error('Error parsing JSON:', error);
                throw new Error('Invalid JSON response');
            }
        });
    })
    .then(data => {
        console.log('Detection response:', data);
        if (data.error) {
            pythonVersionInput.value = 'Detection failed';
            pythonVersionInput.classList.add('error');
            showError(data.error);
        } else if (data.success) {
            pythonVersionInput.value = data.python_version;
            customPythonVersionInput.value = data.python_version;
            pythonVersionInput.classList.remove('error');
            pythonVersionInput.classList.add('success');
        } else {
            pythonVersionInput.value = 'Not detected';
            pythonVersionInput.classList.add('warning');
            showError(data.message || 'Unable to detect Python version');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        pythonVersionInput.value = 'Detection failed';
        pythonVersionInput.classList.add('error');
        showError('Failed to detect Python version. Please try again.');
    })
    .finally(() => {
        hideLoading();
    });
}

    let debounceTimer;
    repoUrlInput.addEventListener('input', (event) => {
        console.log('Repo URL input changed:', event.target.value);
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            if (validateGitHubUrl()) {
                detectPythonVersion(event.target.value.trim());
            }
        }, 500); // Wait for 500ms of inactivity before making the API call
    });

    customPythonVersionInput.addEventListener('input', (event) => {
        console.log('Custom Python version changed:', event.target.value);
        if (event.target.value.trim() !== '') {
            pythonVersionInput.value = 'Custom: ' + event.target.value.trim();
        } else {
            pythonVersionInput.value = 'Not set';
        }
    });

    form.addEventListener('submit', (event) => {
        console.log('Form submitted');
        event.preventDefault();

        if (!validateGitHubUrl()) {
            return;
        }

        showLoading('Setting up repository...');

        const formData = new FormData(form);
        if (customPythonVersionInput.value.trim() !== '') {
            formData.set('python_version', customPythonVersionInput.value.trim());
        }

        fetch('/setup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams(formData)
        })
        .then(response => {
            console.log('Setup response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Setup response:', data);
            hideLoading();
            if (data.error) {
                showError(data.error);
            } else {
                showSuccess(data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            hideLoading();
            showError('An error occurred during setup. Please try again.');
        });
    });
});
