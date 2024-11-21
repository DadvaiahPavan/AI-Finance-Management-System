// Handle transaction form category selection
document.addEventListener('DOMContentLoaded', function() {
    const transactionType = document.getElementById('transaction_type');
    const category = document.getElementById('category');
    
    if (transactionType && category) {
        transactionType.addEventListener('change', function() {
            const type = this.value;
            const options = category.getElementsByTagName('optgroup');
            
            for (let group of options) {
                if (type === 'income' && group.label === 'Income' ||
                    type === 'expense' && group.label === 'Expenses') {
                    group.style.display = '';
                } else {
                    group.style.display = 'none';
                }
            }
            
            // Reset category selection
            category.value = '';
        });
    }
});

// Format currency inputs
function formatCurrency(input) {
    let value = input.value.replace(/[^0-9.]/g, '');
    if (value) {
        value = parseFloat(value).toFixed(2);
        input.value = value;
    }
}

// Update charts based on date range
function updateDateRange() {
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    
    if (startDate && endDate) {
        // Set minimum end date to start date
        endDate.min = startDate.value;
        
        if (endDate.value && startDate.value > endDate.value) {
            endDate.value = startDate.value;
        }
    }
}

// Handle financial goals
function addFinancialGoal(name, target, deadline) {
    const goals = JSON.parse(localStorage.getItem('financialGoals') || '[]');
    goals.push({
        name,
        target,
        deadline,
        progress: 0,
        created: new Date().toISOString()
    });
    localStorage.setItem('financialGoals', JSON.stringify(goals));
    updateGoalsDisplay();
}

function updateGoalsDisplay() {
    const goals = JSON.parse(localStorage.getItem('financialGoals') || '[]');
    const container = document.getElementById('financial-goals');
    if (container) {
        // Update goals display logic here
    }
}

// Handle notifications
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(notification, container.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 150);
        }, 5000);
    }
}

// Export data to CSV
function exportToCSV(data, filename) {
    const csvContent = "data:text/csv;charset=utf-8," + data.map(row => 
        Object.values(row).map(val => `"${val}"`).join(",")
    ).join("\n");
    
    const link = document.createElement("a");
    link.setAttribute("href", encodeURI(csvContent));
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Page loader
document.addEventListener('DOMContentLoaded', function() {
    var loader = document.querySelector('.page-loader');
    var content = document.querySelector('.content-wrapper');
    
    if (loader && content) {
        loader.style.display = 'flex';
        content.style.opacity = '0';
        
        window.addEventListener('load', function() {
            loader.style.opacity = '0';
            setTimeout(function() {
                loader.style.display = 'none';
                content.style.opacity = '1';
            }, 500);
        });
    }
});

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        var target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Navbar animation
var lastScrollTime = 0;
var scrollThrottle = 10;

window.addEventListener('scroll', function() {
    var now = Date.now();
    if (now - lastScrollTime >= scrollThrottle) {
        lastScrollTime = now;
        
        var navbar = document.querySelector('.navbar');
        if (navbar) {
            var scrolled = window.scrollY > 50;
            navbar.style.background = scrolled ? 'rgba(26, 26, 26, 0.95)' : 'linear-gradient(45deg, #1a1a1a, #2c3e50)';
            navbar.style.backdropFilter = scrolled ? 'blur(10px)' : 'none';
            navbar.style.transition = 'all 0.3s ease-in-out';
        }
    }
});

// Card hover effects
var cards = document.querySelectorAll('.card');
var cardAnimationFrame;

cards.forEach(function(card) {
    card.addEventListener('mousemove', function(e) {
        if (cardAnimationFrame) {
            cancelAnimationFrame(cardAnimationFrame);
        }
        
        var rect = this.getBoundingClientRect();
        var x = e.clientX - rect.left;
        var y = e.clientY - rect.top;
        
        var centerX = rect.width / 2;
        var centerY = rect.height / 2;
        
        var rotateX = (y - centerY) / 20;
        var rotateY = -(x - centerX) / 20;
        
        this.style.transform = 'perspective(1000px) rotateX(' + rotateX + 'deg) rotateY(' + rotateY + 'deg) scale3d(1.02, 1.02, 1.02)';
    });
    
    card.addEventListener('mouseleave', function() {
        if (cardAnimationFrame) {
            cancelAnimationFrame(cardAnimationFrame);
        }
        this.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) scale3d(1, 1, 1)';
    });
});

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => new bootstrap.Tooltip(tooltip));
    
    const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    popovers.forEach(popover => new bootstrap.Popover(popover));
});

// Error handling
window.addEventListener('error', function(event) {
    Swal.fire({
        icon: 'error',
        title: 'Oops...',
        text: 'Something went wrong! Please try refreshing the page.',
        confirmButtonText: 'Refresh',
        showCancelButton: true
    }).then(function(result) {
        if (result.isConfirmed) {
            window.location.reload();
        }
    });
});
