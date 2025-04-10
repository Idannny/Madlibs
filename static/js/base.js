document.addEventListener('DOMContentLoaded', function() {

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




