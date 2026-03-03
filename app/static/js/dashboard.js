// --- REPORTS PAGE LOGIC ---
function createLineBarChart(canvasId, title, data, chartType = 'bar') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    const labels = Object.keys(data).sort();
    const values = labels.map(key => data[key]);
    new Chart(ctx, {
        type: chartType,
        data: {
            labels: labels,
            datasets: [{
                label: title,
                data: values,
                backgroundColor: chartType === 'bar' ? 'rgba(78, 115, 223, 0.7)' : 'rgba(78, 115, 223, 0.4)',
                borderColor: 'rgba(78, 115, 223, 1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            maintainAspectRatio: false,
            responsive: true,
            scales: { y: { beginAtZero: true } },
            plugins: { legend: { display: false } }
        }
    });
}

function createCategoryChart(data) {
    const ctx = document.getElementById('categoryChart');
    if (!ctx) return;
    const labels = Object.keys(data);
    const values = Object.values(data);
    const backgroundColors = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b'];
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{ data: values, backgroundColor: backgroundColors.slice(0, labels.length) }]
        }
    });
}

async function loadReportsPage() {
    if (!document.getElementById('dailyChart')) return;
    try {
        const summaryResponse = await fetch('/reports/summary');
        const summaryData = await summaryResponse.json();
        createLineBarChart('dailyChart', 'Daily Totals', summaryData.daily, 'bar');
        createLineBarChart('weeklyChart', 'Weekly Totals', summaryData.weekly, 'bar');
        createLineBarChart('monthlyChart', 'Monthly Totals', summaryData.monthly, 'line');
        
        const categoryResponse = await fetch('/reports/categories');
        const categoryData = await categoryResponse.json();
        createCategoryChart(categoryData);
    } catch (e) { console.error(e); }
}

if (window.location.pathname.startsWith('/reports/')) {
    document.addEventListener('DOMContentLoaded', loadReportsPage);
}
