// Store references to event handlers so we can remove them properly
let currentInput = null;
let currentFocus = -1;

function initializeAutocomplete() {
    const searchInput = document.getElementById("search-input");
    
    // If we already initialized this input, remove old listeners
    if (currentInput === searchInput) {
        return;
    }
    
    // Store reference to current input
    currentInput = searchInput;
    
    // Add event listeners
    searchInput.addEventListener('input', handleInput);
    searchInput.addEventListener('keydown', handleKeyDown);
    
    // Clear any existing autocomplete items
    closeAllLists();
}

// Call initializeAutocomplete when the page loads
document.addEventListener('DOMContentLoaded', initializeAutocomplete);

// Re-initialize autocomplete after each page update
document.addEventListener('turbolinks:load', initializeAutocomplete);

function handleInput(e) {
    let input = e.target;
    closeAllLists();
    
    if (!input.value) return false;
    
    fetch(`/autocomplete?q=${encodeURIComponent(input.value)}`)
        .then(response => response.json())
        .then(suggestions => {
            const container = document.createElement("DIV");
            container.setAttribute("id", "autocomplete-list");
            container.setAttribute("class", "autocomplete-items");
            input.parentNode.appendChild(container);

            suggestions.forEach(suggestion => {
                const item = document.createElement("DIV");
                item.innerHTML = suggestion;
                item.addEventListener("click", function(e) {
                    input.value = this.textContent;
                    closeAllLists();
                });
                container.appendChild(item);
            });
        });
}

function handleKeyDown(e) {
    let x = document.getElementById("autocomplete-list");
    if (x) x = x.getElementsByTagName("div");
    if (e.keyCode == 40) {
        currentFocus++;
        addActive(x);
    } else if (e.keyCode == 38) {
        currentFocus--;
        addActive(x);
    } else if (e.keyCode == 13) {
        e.preventDefault();
        if (currentFocus > -1) {
            if (x) x[currentFocus].click();
        }
    }
}

function addActive(x) {
    if (!x) return false;
    removeActive(x);
    if (currentFocus >= x.length) currentFocus = 0;
    if (currentFocus < 0) currentFocus = (x.length - 1);
    x[currentFocus].classList.add("autocomplete-active");
}

function removeActive(x) {
    for (var i = 0; i < x.length; i++) {
        x[i].classList.remove("autocomplete-active");
    }
}

function closeAllLists(elmnt) {
    var x = document.getElementsByClassName("autocomplete-items");
    for (var i = 0; i < x.length; i++) {
        if (elmnt != x[i] && elmnt != currentInput) {
            x[i].parentNode.removeChild(x[i]);
        }
    }
}

document.addEventListener("click", function (e) {
    closeAllLists(e.target);
});

// Initialize on page load and after form submission
document.addEventListener('DOMContentLoaded', initializeAutocomplete);
document.querySelector('form').addEventListener('submit', function() {
    setTimeout(initializeAutocomplete, 100); // Re-initialize after form submission
}); 