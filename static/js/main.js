document.addEventListener('DOMContentLoaded', function() {
    // File upload handling
    const uploadForm = document.getElementById('uploadForm');
    const uploadProgress = document.getElementById('uploadProgress');
    const uploadButton = document.getElementById('uploadButton');

    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            const fileInput = document.getElementById('file');
            if (!fileInput.files.length) {
                e.preventDefault();
                alert('Please select a file to upload');
                return;
            }

            uploadButton.disabled = true;
            uploadProgress.classList.remove('d-none');
            uploadButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        });
    }

    // Citation copy functionality
    const copyButtons = document.querySelectorAll('.copy-citation');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const citation = this.getAttribute('data-citation');
            navigator.clipboard.writeText(citation).then(() => {
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="bi bi-check"></i> Copied!';
                setTimeout(() => {
                    this.innerHTML = originalText;
                }, 2000);
            });
        });
    });

    // Initialize CKEditor if we're on the notebook page
    if (document.getElementById('editor')) {
        let editor;

        ClassicEditor
            .create(document.querySelector('#editor'))
            .then(newEditor => {
                editor = newEditor;
            })
            .catch(error => {
                console.error(error);
            });

        // Handle citation search
        const citationSearch = document.getElementById('citationSearch');
        const citationResults = document.getElementById('citationResults');
        let searchTimeout;

        citationSearch.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const query = this.value.trim();
                if (query.length >= 3) {
                    fetch(`/search?q=${encodeURIComponent(query)}&format=json`)
                        .then(response => response.json())
                        .then(data => {
                            citationResults.innerHTML = data.results.map(paper => `
                                <button class="list-group-item list-group-item-action" data-citation="${paper.title}">
                                    ${paper.title}
                                    <small class="d-block text-muted">${paper.authors.join(', ')}</small>
                                </button>
                            `).join('');

                            // Add click handlers for citations
                            citationResults.querySelectorAll('button').forEach(btn => {
                                btn.addEventListener('click', function() {
                                    const citation = this.dataset.citation;
                                    editor.model.change(writer => {
                                        const content = writer.createText(`[${citation}]`);
                                        editor.model.insertContent(content);
                                    });
                                });
                            });
                        });
                }
            }, 300);
        });

        // Handle image generation
        const generateImageBtn = document.getElementById('generateImage');
        const imagePrompt = document.getElementById('imagePrompt');
        const generatedImages = document.getElementById('generatedImages');

        generateImageBtn.addEventListener('click', function() {
            const prompt = imagePrompt.value.trim();
            if (prompt) {
                generateImageBtn.disabled = true;
                generateImageBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Generating...';

                fetch('/generate-image', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ prompt }),
                })
                .then(response => response.json())
                .then(data => {
                    const img = document.createElement('img');
                    img.src = data.url;
                    img.className = 'img-fluid mb-2';
                    img.onclick = function() {
                        editor.model.change(writer => {
                            const imageElement = writer.createElement('image', {
                                src: data.url
                            });
                            editor.model.insertContent(imageElement);
                        });
                    };
                    generatedImages.insertBefore(img, generatedImages.firstChild);
                })
                .finally(() => {
                    generateImageBtn.disabled = false;
                    generateImageBtn.innerHTML = '<i class="bi bi-image"></i> Generate Image';
                });
            }
        });

        // Handle plagiarism check
        const checkPlagiarismBtn = document.getElementById('checkPlagiarism');
        const plagiarismResults = document.getElementById('plagiarismResults');

        checkPlagiarismBtn.addEventListener('click', function() {
            const content = editor.getData();
            checkPlagiarismBtn.disabled = true;
            checkPlagiarismBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Checking...';

            fetch('/check-plagiarism', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ content }),
            })
            .then(response => response.json())
            .then(data => {
                plagiarismResults.innerHTML = `
                    <div class="alert ${data.similarity > 20 ? 'alert-warning' : 'alert-success'}">
                        <strong>Similarity Score:</strong> ${data.similarity}%
                        ${data.matches.map(match => `
                            <div class="mt-2">
                                <small class="text-muted">Similar to: ${match.source}</small>
                            </div>
                        `).join('')}
                    </div>
                `;
            })
            .finally(() => {
                checkPlagiarismBtn.disabled = false;
                checkPlagiarismBtn.innerHTML = '<i class="bi bi-shield-check"></i> Check Content';
            });
        });
    }
});