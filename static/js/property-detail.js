document.addEventListener('DOMContentLoaded', function() {
    const resultRows = document.querySelectorAll('.results-table tbody tr');
    resultRows.forEach(row => {
        row.addEventListener('click', function() {
            const sql = this.querySelector('td:first-child').textContent.trim();
            console.log('Clicked property with SQL:', sql);
            window.location.href = `/property/${sql}`;
        });
    });
}); 