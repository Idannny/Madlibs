const stripeKey = document.querySelector('.credit-packages').dataset.stripeKey;
const stripe = Stripe(stripeKey);

async function purchaseCredits(credits, event) {

    try {
        const button = event.target;
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = 'Processing...';
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        console.log("stripejs csrf",csrfToken);
        console.log("stripejs pub ",stripe);

        const response = await fetch('/create-checkout-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken 
            },
            body: JSON.stringify({ credits: credits })
        });

        console.log("in function respi");
        console.log(response.body);

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const session = await response.json();
        
        const result = await stripe.redirectToCheckout({
            sessionId: session.id
        });
        console.log('Session ID:', session.id);


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
        button.addEventListener('click', function(event) {
            const credits =  parseInt(this.getAttribute('data-credits'), 10);
            console.log('Credits:', credits);
            purchaseCredits.call(this, credits, event);
        });
    });

}

document.addEventListener('DOMContentLoaded', function() {
    initializeButtons();
});