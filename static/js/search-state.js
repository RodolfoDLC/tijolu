// Save search state when results are loaded
document.addEventListener('DOMContentLoaded', function() {
    // Save search query and scroll position when leaving the page
    window.addEventListener('beforeunload', function() {
        const searchQuery = document.querySelector('.search-form input[type="text"]').value;
        const scrollPosition = window.scrollY;
        sessionStorage.setItem('lastSearchQuery', searchQuery);
        sessionStorage.setItem('lastScrollPosition', scrollPosition);
    });

    // Restore search state if coming back to the page
    if (performance.navigation.type === 2 || document.referrer.includes('/property/')) {
        const lastSearchQuery = sessionStorage.getItem('lastSearchQuery');
        const lastScrollPosition = sessionStorage.getItem('lastScrollPosition');
        
        if (lastSearchQuery) {
            const searchInput = document.querySelector('.search-form input[type="text"]');
            if (searchInput && !searchInput.value) {
                searchInput.value = lastSearchQuery;
                searchInput.form.submit();
            }
        }

        if (lastScrollPosition) {
            window.addEventListener('load', function() {
                window.scrollTo(0, parseInt(lastScrollPosition));
            });
        }
    }
});

// Add the new function for property detail back button
function goBackToSearch() {
    if (document.referrer.includes('/search')) {
        window.history.back();
        return false;
    }
    return true;
} 