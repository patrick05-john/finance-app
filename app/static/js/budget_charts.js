document.addEventListener('DOMContentLoaded', function() {
    // 1. Fetch the data securely embedded in the HTML
    const dataElement = document.getElementById('budget-chart-data');
    if (!dataElement) return;
    
    const chartData = JSON.parse(dataElement.textContent);
    
    // 2. Define our aesthetic color palette to match the Dashboard
    const colors = {
        primary: '#4e73df',   // Main Blue
        success: '#1cc88a',   // Green
        warning: '#f6c23e',   // Yellow
        danger: '#e74a3b',    // Red
        info: '#36b9cc',      // Light Blue
        dark: '#5a5c69',      // Dark Gray
        neutral: '#e3e6f0'    // Empty State Gray
    };

    const piePalette = [colors.primary, colors.info, colors.success, colors.warning, colors.danger, colors.dark];

    // --- CHART 1: Budget vs Actual (Bar Chart) ---
    const budgetCtx = document.getElementById('budgetActualChart');
    if (budgetCtx) {
        new Chart(budgetCtx, {
            type: 'bar',
            data: {
                labels: ['Budget Overview'],
                datasets: [
                    {
                        label: 'Total Budgeted',
                        data: [chartData.budget.total],
                        backgroundColor: 'rgba(78, 115, 223, 0.2)', // Light blue fill
                        borderColor: colors.primary,
                        borderWidth: 2,
                        borderRadius: 4
                    },
                    {
                        label: 'Amount Spent',
                        data: [chartData.budget.spent],
                        backgroundColor: chartData.budget.spent > chartData.budget.total ? 'rgba(231, 74, 59, 0.8)' : 'rgba(28, 200, 138, 0.8)', // Red if over budget, else green
                        borderColor: chartData.budget.spent > chartData.budget.total ? colors.danger : colors.success,
                        borderWidth: 2,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) { return '₱' + value; },
                            font: { family: 'system-ui, -apple-system, sans-serif' }
                        },
                        grid: { borderDash: [2, 2], drawBorder: false }
                    },
                    x: { grid: { display: false } }
                },
                plugins: {
                    legend: { position: 'bottom', labels: { usePointStyle: true, padding: 20 } },
                    tooltip: {
                        callbacks: {
                            label: function(context) { return context.dataset.label + ': ₱' + context.parsed.y.toFixed(2); }
                        }
                    }
                }
            }
        });
    }

    // --- CHART 2: Expenses by Category (Doughnut Chart) ---
    const categoryCtx = document.getElementById('expenseCategoryChart');
    if (categoryCtx) {
        // Aggregate expenses by category dynamically
        const categoryTotals = {};
        chartData.expenses.forEach(exp => {
            if (categoryTotals[exp.category]) {
                categoryTotals[exp.category] += exp.amount;
            } else {
                categoryTotals[exp.category] = exp.amount;
            }
        });

        const labels = Object.keys(categoryTotals);
        const data = Object.values(categoryTotals);

        // Handle empty state if there are no expenses
        if (labels.length === 0) {
            labels.push('No Expenses Yet');
            data.push(1);
        }

        new Chart(categoryCtx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: data.length === 1 && labels[0] === 'No Expenses Yet' ? [colors.neutral] : piePalette,
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%', // Makes the doughnut ring thinner/sleeker
                plugins: {
                    legend: { 
                        position: 'right',
                        labels: { usePointStyle: true, padding: 15, font: { family: 'system-ui, -apple-system, sans-serif' } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                if (labels[0] === 'No Expenses Yet') return ' No data to display';
                                return ' ' + context.label + ': ₱' + context.parsed.toFixed(2);
                            }
                        }
                    }
                }
            }
        });
    }
});
