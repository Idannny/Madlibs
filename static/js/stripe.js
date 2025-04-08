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
                'X-CSRFToken': csrfToken 
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

function initializeButtons() {
    const buttons = document.querySelectorAll('.credit-option');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            const credits = this.getAttribute('data-credits');
            purchaseCredits(credits);
        });
    });

}

document.addEventListener('DOMContentLoaded', function() {
    initializeButtons();
});