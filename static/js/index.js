document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const loadingScreen = document.getElementById('loading-screen');
    const signInButton = document.querySelector('.btn-sign-in');

    // Handle form submission (e.g., Purchase Tokens form)
    if (form) {
        form.addEventListener('submit', function() {
            console.log("submitted form")
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
    
   
    window.onReCaptchaSuccess = function() {
        submitButton.disabled = false;
    };


    form.addEventListener('submit', function(e) {
        e.preventDefault();

        loadingScreen.classList.remove('hidden');

        const submitUrl = form.getAttribute('data-submit-url');
        const csrfToken = document.querySelector('input[name="csrf_token"]').value;
        const recaptchaResponse = grecaptcha.getResponse();
        console.log("Recaptcha:  ",recaptchaResponse)
        const formData = new FormData(form);

        if (!recaptchaResponse) {
            alert('Please complete the CAPTCHA');
            return;
        }

        formData.append('g-recaptcha-response', recaptchaResponse);
        formData.append('csrf_token', csrfToken);
        
        submitButton.disabled = true;


        fetch(submitUrl, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            console.log('Response status:', response.status); 
            return response.json().then(data => {
                if (!response.ok) {
                    console.error('Error response data:', data); 
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return data;
            });
        })
        .then(data => {
            // Hide loading screen
            loadingScreen.classList.add('hidden');
            
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
            loadingScreen.classList.add('hidden');
            console.error('Error:', error);
            alert('An error occurred while generating your story. Please try again.');
        })
        .finally(() => {
            grecaptcha.reset();
            submitButton.disabled = true;
            loadingScreen.classList.add('hidden');
        });
    });
});


