const stripe = Stripe('{{ stripe_key }}');
    
async function purchaseCredits(credits) {
    try {
        const button = event.target;
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = 'Processing...';

        const response = await fetch('/create-checkout-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
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

function viewStory(storyId) {
    window.location.href = `/story/${storyId}`;
}