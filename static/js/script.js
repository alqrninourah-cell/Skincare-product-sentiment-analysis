// JavaScript for Skincare Sentiment Analysis website

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Lucide icons
    lucide.createIcons();



    // Form validation and loading animation
    const form = document.getElementById('recommendationForm');
    if (form) {
        const skinTypeSelect = document.getElementById('skin_type');
        const concernsTextarea = document.getElementById('concerns');
        const submitBtn = document.getElementById('submitBtn');
        const btnText = document.getElementById('btnText');
        const loadingSpinner = document.getElementById('loadingSpinner');

        // Real-time validation
        skinTypeSelect.addEventListener('change', function() {
            validateSkinType();
        });

        concernsTextarea.addEventListener('input', function() {
            validateConcerns();
        });

        function validateSkinType() {
            const errorElement = skinTypeSelect.parentNode.querySelector('.error-message');
            if (!skinTypeSelect.value) {
                skinTypeSelect.classList.add('form-error');
                if (!errorElement) {
                    const error = document.createElement('p');
                    error.className = 'error-message';
                    error.textContent = 'Please select your skin type.';
                    skinTypeSelect.parentNode.appendChild(error);
                }
                return false;
            } else {
                skinTypeSelect.classList.remove('form-error');
                if (errorElement) {
                    errorElement.remove();
                }
                return true;
            }
        }

        function validateConcerns() {
            const errorElement = concernsTextarea.parentNode.querySelector('.error-message');
            if (concernsTextarea.value.trim().length < 3) {
                concernsTextarea.classList.add('form-error');
                if (!errorElement) {
                    const error = document.createElement('p');
                    error.className = 'error-message';
                    error.textContent = 'Please provide at least 3 characters describing your concerns.';
                    concernsTextarea.parentNode.appendChild(error);
                }
                return false;
            } else {
                concernsTextarea.classList.remove('form-error');
                if (errorElement) {
                    errorElement.remove();
                }
                return true;
            }
        }

        form.addEventListener('submit', function(e) {
            const isSkinTypeValid = validateSkinType();
            const isConcernsValid = validateConcerns();

            if (!isSkinTypeValid || !isConcernsValid) {
                e.preventDefault();
                return;
            }

            // Show loading state
            submitBtn.disabled = true;
            btnText.textContent = 'Analyzing...';
            loadingSpinner.classList.remove('hidden');

            // Add loading animation to form
            form.style.opacity = '0.7';
            form.style.pointerEvents = 'none';

            // Show progress indicator
            showProgressIndicator();
        });

        function showProgressIndicator() {
            const progressContainer = document.createElement('div');
            progressContainer.id = 'progressContainer';
            progressContainer.className = 'mt-4 text-center';
            progressContainer.innerHTML = `
                <div class="inline-block">
                    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500 mx-auto"></div>
                    <p class="mt-2 text-sm text-gray-600">Analyzing your skin type and finding recommendations...</p>
                </div>
            `;
            form.appendChild(progressContainer);
        }
    }

    // Enhanced form validation for review submission
    const reviewForm = document.getElementById('reviewForm');
    if (reviewForm) {
        const ratingInput = document.getElementById('rating');
        const reviewText = document.getElementById('review_text');

        reviewForm.addEventListener('submit', function(e) {
            let isValid = true;

            // Validate rating
            if (!ratingInput.value || ratingInput.value < 1 || ratingInput.value > 5) {
                showError('rating', 'Please select a rating between 1 and 5 stars.');
                isValid = false;
            } else {
                hideError('rating');
            }

            // Validate review text
            if (!reviewText.value.trim() || reviewText.value.trim().length < 10) {
                showError('review_text', 'Please write a review with at least 10 characters.');
                isValid = false;
            } else {
                hideError('review_text');
            }

            if (!isValid) {
                e.preventDefault();
            }
        });

        function showError(fieldId, message) {
            const field = document.getElementById(fieldId);
            const errorElement = field.parentNode.querySelector('.error-message');

            field.classList.add('form-error');
            if (!errorElement) {
                const error = document.createElement('p');
                error.className = 'error-message';
                error.textContent = message;
                field.parentNode.appendChild(error);
            }
        }

        function hideError(fieldId) {
            const field = document.getElementById(fieldId);
            const errorElement = field.parentNode.querySelector('.error-message');

            field.classList.remove('form-error');
            if (errorElement) {
                errorElement.remove();
            }
        }
    }

    // Star rating functionality
    const starContainers = document.querySelectorAll('.star-rating');
    starContainers.forEach(container => {
        const stars = container.querySelectorAll('.star');
        const ratingInput = container.querySelector('input[type="hidden"]');

        stars.forEach((star, index) => {
            star.addEventListener('click', function() {
                const rating = index + 1;
                ratingInput.value = rating;

                // Update star display
                stars.forEach((s, i) => {
                    if (i < rating) {
                        s.classList.add('filled');
                    } else {
                        s.classList.remove('filled');
                    }
                });
            });

            star.addEventListener('mouseover', function() {
                stars.forEach((s, i) => {
                    if (i <= index) {
                        s.classList.add('active');
                    } else {
                        s.classList.remove('active');
                    }
                });
            });

            star.addEventListener('mouseout', function() {
                stars.forEach(s => s.classList.remove('active'));
            });
        });
    });

    // Smooth scrolling for navigation
    const navLinks = document.querySelectorAll('nav a');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href.startsWith('#')) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });
    });

    // Add fade-in animation for content
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observe elements for animation
    const animatedElements = document.querySelectorAll('.grid > div, .bg-white');
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
});
