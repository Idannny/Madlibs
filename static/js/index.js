const stripe = Stripe('{{ config["STRIPE_PUBLISHABLE_KEY"] }}');
    
async function purchaseCredits(credits) {
        console.log("Attempting to purchase credits: ")
    try {

        const button = event.target;
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = 'Processing...';
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        console.log("CSRF Token:", csrfToken);
        const response = await fetch('/create-checkout-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken // Include CSRF token
            },
            body: JSON.stringify({ credits: credits })
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const session = await response.json();
        
        const result = await stripe.redirectToCheckout({
            sessionId: session.id
        });

        if (result.error) {
            throw new Error(result.error.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('There was a problem with your payment. Please try again.');
        
        const button = event.target;
        button.disabled = false;
        button.textContent = originalText;
    }
}


function showLoadingScreen() {
    const loadingScreen = document.getElementById('loading-screen');
    loadingScreen.classList.remove('hidden');
}


document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('submit-form');
    // const loadingScreen = document.querySelector('loading-screen');
    // 2const resultDiv = document.getElementById('result');
    
    initializeButtons();
    initializeForm(form);
});


function initializeForm(daform) {
    const form = daform;
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
}

function initializeButtons() {
    const buttons = document.querySelectorAll('.credit-option');

    buttons.forEach(button => {
        button.addEventListener('click', function() {
            const credits = this.getAttribute('data-credits');
            purchaseCredits(credits);
        });
    });
}