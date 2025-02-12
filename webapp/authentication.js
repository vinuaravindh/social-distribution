// Function to get CSRF token from cookies
function getCSRFToken() {
    const cookie = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}

function getAuthorId() {
    const cookie = document.cookie
        .split('; ')
        .find(row => row.startsWith('author_id='));
    return cookie ? cookie.split('=')[1] : null;
}

// Function to handle login
async function handleLogin(event) {
    event.preventDefault();

    const emailField = document.getElementById('email');
    const passwordField = document.getElementById('password');
    const nextField = document.getElementById('next');
    const errorMessage = document.getElementById('error-message');

    const email = emailField ? emailField.value.trim() : '';
    const password = passwordField ? passwordField.value : '';
    const next = nextField ? nextField.value : '/';

    if (errorMessage) {
        errorMessage.textContent = ''; // Clear previous errors
    }

    try {
        const response = await fetch('/api/login/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({ email, password, next }),
            credentials: 'include', // Include cookies
        });

        const data = await response.json();

        if (response.ok) {
            // Redirect to 'next' URL or default
            const redirectUrl = data.next || '/';
            window.location.href = redirectUrl;
        } else {
            // Display error messages
            if (errorMessage) {
                errorMessage.textContent = data.detail || 'Login failed. Please try again.';
            } else {
                alert(data.detail || 'Login failed. Please try again.');
            }
        }
    } catch (error) {
        console.error('Error during login:', error);
        if (errorMessage) {
            errorMessage.textContent = 'An error occurred. Please try again later.';
        } else {
            alert('An error occurred. Please try again later.');
        }
    }
}

// Function to handle signup
async function handleSignup(event) {
    event.preventDefault();

    const displayNameField = document.getElementById('display_name');
    const emailField = document.getElementById('email');
    const passwordField = document.getElementById('password');
    const confirmPasswordField = document.getElementById('confirm_password');
    const nextField = document.getElementById('next');
    const errorMessage = document.getElementById('error-message');

    const displayName = displayNameField ? displayNameField.value.trim() : '';
    const email = emailField ? emailField.value.trim() : '';
    const password = passwordField ? passwordField.value : '';
    const confirmPassword = confirmPasswordField ? confirmPasswordField.value : '';
    const next = nextField ? nextField.value : '/';

    if (errorMessage) {
        errorMessage.textContent = ''; // Clear previous errors
    }

    if (password !== confirmPassword) {
        if (errorMessage) {
            errorMessage.textContent = 'Passwords do not match.';
        } else {
            alert('Passwords do not match.');
        }
        return;
    }

    try {
        const response = await fetch('/api/signup/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({ display_name: displayName, email, password, confirm_password: confirmPassword, next }),
            credentials: 'include', // Include cookies
        });

        const data = await response.json();

        if (response.ok) {
            // Redirect to 'next' URL or default
            const redirectUrl = data.next || '/';
            window.location.href = redirectUrl;
        } else {
            // Display error messages
            if (errorMessage) {
                // Handle specific field errors if provided
                if (data.email) {
                    errorMessage.textContent = data.email.join(' ');
                } else if (data.display_name) {
                    errorMessage.textContent = data.display_name.join(' ');
                } else if (data.detail) {
                    errorMessage.textContent = data.detail;
                } else {
                    errorMessage.textContent = 'Signup failed. Please check your inputs.';
                }
            } else {
                alert('Signup failed. Please check your inputs.');
            }
        }
    } catch (error) {
        console.error('Error during signup:', error);
        if (errorMessage) {
            errorMessage.textContent = 'An error occurred. Please try again later.';
        } else {
            alert('An error occurred. Please try again later.');
        }
    }
}

// Function to handle logout
async function handleLogout() {
    try {
        const response = await fetch('/api/logout/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            credentials: 'include', // Include cookies
        });

        if (response.ok) {
            // Redirect to login page
            window.location.href = '/node/';
        } else {
            alert('Logout failed. Please try again.');
        }
    } catch (error) {
        console.error('Error during logout:', error);
        alert('An error occurred. Please try again later.');
    }
}

// Function to check authentication
async function checkAuth() {
    try {
        const response = await fetch('/api/user-info/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include', // Include cookies
        });

        return response.ok; // true if authenticated
    } catch (error) {
        console.error('Error checking authentication:', error);
        return false;
    }
}

// Attach event listeners
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    const signupForm = document.getElementById('signup-form');
    if (signupForm) {
        signupForm.addEventListener('submit', handleSignup);
    }

    const logoutButton = document.getElementById('logout-button');
    if (logoutButton) {
        logoutButton.addEventListener('click', handleLogout);
    }
});

window.getCSRFToken = getCSRFToken;
window.getAuthorId = getAuthorId;