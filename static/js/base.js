document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const loadingScreen = document.getElementById('loading-screen');

    // Handle form submission (e.g., Purchase Tokens form)
    if (form) {
        form.addEventListener('submit', function() {
            console.log("submitted datas")
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
    loadingScreen.classList.remove('hidden');
}


document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('submit-form');
    const loadingScreen = document.querySelector('loading-screen');
    const resultDiv = document.getElementById('result');
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const recaptchaResponse = grecaptcha.getResponse();
        if (!recaptchaResponse) {
            alert('Please complete the CAPTCHA');
            return;
        }

        loadingScreen.style.display = 'none';
        resultDiv.style.display = 'none';

        let formData = new FormData(form);
        formData.append('g-recaptcha-response', recaptchaResponse);
        
        fetch('{{ url_for("submit") }}', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loadingScreen.style.display = 'none';
            
            if (data.error) {
                alert(data.error);
                if (data.require_login) {
                    window.location.href = '{{ url_for("login") }}';
                } else if (data.require_payment) {
                    const purchaseSection = document.querySelector('.purchase-credits');
                    if (purchaseSection) {
                        purchaseSection.scrollIntoView({ behavior: 'smooth' });
                    }
                }
            } else {
                document.getElementById('story').textContent = data.story;
                document.getElementById('image').src = data.image;
                resultDiv.style.display = 'block';
                resultDiv.scrollIntoView({ behavior: 'smooth' });
            }
        })
        .catch(error => {
            loadingScreen.style.display = 'none';
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
        })
        .finally(() => {
            grecaptcha.reset();
        });
    });
});


