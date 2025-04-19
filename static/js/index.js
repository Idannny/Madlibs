document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const loadingScreen = document.getElementById('loading-screen');
    const signInButton = document.querySelector('.btn-sign-in');

    // Handle form submission (e.g., Purchase Tokens form)
    if (form) {
        form.addEventListener('submit', function() {
            loadingScreen.style.display = 'flex';
        });
    }

    if (signInButton) {
        signInButton.addEventListener('click', function(event) {
            if (!session.get('user')) {
                event.preventDefault(); // Prevent default action (redirect)
                window.location.href = "{{ url_for('login') }}"; // Redirect to login route

            }
        });
    }
});


document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('submit-form');
    const loadingScreen = document.getElementById('loading-screen');
    const resultDiv = document.getElementById('result');
    const submitButton = document.getElementById('submit-button'); 
    const recaptchaResponse = grecaptcha.getResponse();
    const freeTries = parseInt(form.getAttribute('data-free-tries'), 10);

    let recaptchaPassed = false;

    if (freeTries <= 0 && recaptchaResponse == false ) {
        submitButton.disabled = true;
    }

    function updateButtonState() {
        // HTML5 form validation
        const formValid = form.checkValidity();
        // Only enable if both are true
        submitButton.disabled = !(formValid && recaptchaPassed);
    }

    // Listen for input changes on all form fields
    Array.from(form.elements).forEach(el => {
        el.addEventListener('input', updateButtonState);
        el.addEventListener('change', updateButtonState);
    });

    // Called by reCAPTCHA when solved
    window.onReCaptchaSuccess = function() {
        recaptchaPassed = true;
        updateButtonState();
    };

    // Called by reCAPTCHA when expired or reset
    window.onReCaptchaExpired = function() {
        recaptchaPassed = false;
        updateButtonState();
    };

    // Initial state
    updateButtonState();


    form.addEventListener('submit', function(e) {
        e.preventDefault();
 
        loadingScreen.classList.remove('hidden');

        const submitUrl = form.getAttribute('data-submit-url');
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        const recaptchaResponse = grecaptcha.getResponse();
        const formData = new FormData(form);

        if (!recaptchaResponse) {
            alert('Please complete the CAPTCHA');
            return;
        }


        formData.append('g-recaptcha-response', recaptchaResponse);
        formData.append('csrf_token', csrfToken);
        
        fetch(submitUrl, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            console.log('Response status:', response.status); 
            loadingScreen.classList.add('hidden');
        
            // Check if the response is JSON
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return response.json().then(data => {
                    if (!response.ok) {
                        console.error('Error response data:', data); 
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return data;
                });
            } else {
                // Handle non-JSON response
                console.error('Expected JSON response but got:', contentType);
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
            grecaptcha.reset();
            submitButton.disabled = true;
            loadingScreen.style.display = 'none';


        });
    });
});


