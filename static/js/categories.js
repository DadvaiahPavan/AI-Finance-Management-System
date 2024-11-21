// Function to update categories based on transaction type
document.addEventListener('DOMContentLoaded', function() {
    var transactionType = document.getElementById('transaction_type');
    var categorySelect = document.getElementById('category');

    if (transactionType && categorySelect) {
        transactionType.addEventListener('change', function() {
            var type = this.value;
            var optgroups = categorySelect.getElementsByTagName('optgroup');
            
            for (var i = 0; i < optgroups.length; i++) {
                var group = optgroups[i];
                if ((type === 'income' && group.label === 'Income') ||
                    (type === 'expense' && group.label === 'Expenses')) {
                    group.style.display = '';
                } else {
                    group.style.display = 'none';
                }
            }
            
            // Reset category selection
            categorySelect.value = '';
        });

        // Initialize categories on page load
        var event = new Event('change');
        transactionType.dispatchEvent(event);
    }
});
