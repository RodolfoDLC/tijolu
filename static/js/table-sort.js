document.addEventListener('DOMContentLoaded', function() {
    const table = document.getElementById('resultsTable');
    if (!table) return;

    const headers = table.querySelectorAll('th.sortable');
    headers.forEach(header => {
        header.addEventListener('click', function() {
            const column = this.dataset.sort;
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const currentDirection = this.classList.contains('asc') ? 'desc' : 'asc';

            // Remove sorting classes from all headers
            headers.forEach(h => h.classList.remove('asc', 'desc'));
            this.classList.add(currentDirection);

            // Sort the rows
            rows.sort((a, b) => {
                const aCell = a.querySelector(`td[data-value]:nth-child(${this.cellIndex + 1})`);
                const bCell = b.querySelector(`td[data-value]:nth-child(${this.cellIndex + 1})`);
                
                const aValue = aCell.dataset.value;
                const bValue = bCell.dataset.value;

                // Check if values are numbers
                const aNum = parseFloat(aValue);
                const bNum = parseFloat(bValue);
                
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return currentDirection === 'asc' ? aNum - bNum : bNum - aNum;
                }
                
                // Sort as strings
                return currentDirection === 'asc' 
                    ? aValue.localeCompare(bValue, 'pt-BR') 
                    : bValue.localeCompare(aValue, 'pt-BR');
            });

            // Reorder the table
            tbody.innerHTML = '';
            rows.forEach(row => tbody.appendChild(row));
        });
    });
}); 