document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const loadingScreen = document.getElementById('loading-screen');

    // Handle form submission (e.g., Purchase Tokens form)
    if (form) {
        form.addEventListener('submit', function() {
            console.log("submitted form")
            loadingScreen.style.display = 'flex';
        });
    }

    // Handle Sign In with Google button click
    const signInButton = document.querySelector('.btn-sign-in');
    if (signInButton) {
        signInButton.addEventListener('click', function(event) {
            if (!session.get('user')) {
                event.preventDefault(); // Prevent default action (redirect)
                window.location.href = "{{ url_for('login') }}"; // Redirect to login route

            }
        });
    }
});

function showLoadingScreen() {
    const loadingScreen = document.getElementById('loading-screen');
    // loadingScreen.classList.remove('hidden');
}


document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('submit-form');
    const loadingScreen = document.getElementById('loading-screen');
    const resultDiv = document.getElementById('result');
    
    if (!form) return; // Exit if form not found
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const recaptchaResponse = grecaptcha.getResponse();
        if (!recaptchaResponse) {
            alert('Please complete the CAPTCHA');
            return;
        }

        // Show loading screen and hide result
        loadingScreen.classList.remove('hidden');
        resultDiv.classList.remove('hidden');

        let formData = new FormData(form);
        formData.append('g-recaptcha-response', recaptchaResponse);

        const csrfToken = document.querySelector('input[name="csrf_token"]').value;
        formData.append('csrf_token', csrfToken);
        
        const submitUrl = form.getAttribute('data-submit-url');
        
        fetch(submitUrl, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Hide loading screen
            loadingScreen.classList.add('hidden');
            resultDiv.classList.add('hidden');

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
            loadingScreen.classList.add('hidden');
            alert('An error occurred while generating your story. Please try again.');
        })
        .finally(() => {
            grecaptcha.reset();
        });
    });
});


