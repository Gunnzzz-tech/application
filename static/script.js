// Toast notification function
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
}

// File upload handler
const fileInput = document.getElementById('cv');
const fileLabel = document.getElementById('fileLabel');
const fileNameSpan = document.getElementById('fileName');

fileInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        const iconHtml = '<i data-lucide="check-circle-2" class="file-icon"></i>';
        fileNameSpan.textContent = file.name;
        fileLabel.classList.add('has-file');

        // Re-initialize Lucide icons for the new icon
        lucide.createIcons();
    }
});

// Form reset handler
const resetBtn = document.getElementById('resetBtn');
const jobForm = document.getElementById('jobForm');

resetBtn.addEventListener('click', function() {
    jobForm.reset();
    fileNameSpan.textContent = 'Click to upload your resume (PDF, DOC, DOCX)';
    fileLabel.classList.remove('has-file');
    showToast('Form cleared', 'info');

    // Re-initialize Lucide icons
    lucide.createIcons();
});

