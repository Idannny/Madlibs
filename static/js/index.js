document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('submit-form');
    const submitButton = document.getElementById('submit-button');
    const loadingScreen = document.getElementById('loading-screen');
    const resultDiv = document.getElementById('result');
    const freeTries = parseInt(form?.getAttribute('data-free-tries') || "0", 10);
    const credits = parseInt(form?.getAttribute('data-credits') || "0", 10);
    let recaptchaPassed = false;

    function updateButtonState() {
        if (!form || !submitButton) return;
        const formValid = form.checkValidity();
        const hasCredits = (credits > 0) || (freeTries > 0);
        submitButton.disabled = !(formValid && hasCredits && recaptchaPassed);
    }

    // Listen for input changes on all form fields
    if (form) {
        Array.from(form.elements).forEach(el => {
            el.addEventListener('input', updateButtonState);
            el.addEventListener('change', updateButtonState);
        });
    }

    // reCAPTCHA callbacks
    window.onReCaptchaSuccess = function() {
        recaptchaPassed = true;
        updateButtonState();
    };
    window.onReCaptchaExpired = function() {
        recaptchaPassed = false;
        updateButtonState();
    };

    // Set initial state
    updateButtonState();

    // Handle form submission
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            loadingScreen.classList.remove('hidden');

            const submitUrl = form.getAttribute('data-submit-url');
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            const recaptchaResponse = grecaptcha.getResponse();
            const formData = new FormData(form);

            formData.append('g-recaptcha-response', recaptchaResponse);
            formData.append('csrf_token', csrfToken);

            fetch(submitUrl, {
                method: 'POST',
                body: formData
            })
            .then(response => {
                loadingScreen.classList.add('hidden');
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return response.json().then(data => {
                        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                        return data;
                    });
                } else {
                    throw new Error('Server returned a non-JSON response');
                }
            })
            .then(data => {
                if (data.error) {
                    alert(data.error);
                    if (data.require_login) {
                        window.location.href = '/login';
                    } else if (data.require_payment) {
                        const purchaseSection = document.querySelector('.purchase-credits');
                        if (purchaseSection) {
                            purchaseSection.scrollIntoView({ behavior: 'smooth' });
                        }
                    }
                } else {
                    document.getElementById('story').textContent = data.story;
                    document.getElementById('image').src = data.image;
                    resultDiv.classList.remove('hidden');
                    resultDiv.scrollIntoView({ behavior: 'smooth' });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while generating your story. Please try again: ', error);
            })
            .finally(() => {
                if (typeof grecaptcha !== "undefined") {
                    grecaptcha.reset();
                }
                recaptchaPassed = false;
                updateButtonState();
                loadingScreen.style.display = 'none';
            });
        });
    }
});
