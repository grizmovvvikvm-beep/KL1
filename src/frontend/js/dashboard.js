// Real-time metrics updates
function startLiveMetrics() {
    setInterval(() => {
        fetch('/api/system/info')
            .then(response => response.json())
            .then(data => {
                updateDashboardMetrics(data);
            });
    }, 5000);
}

function updateDashboardMetrics(data) {
    // Update CPU gauge
    updateGauge('cpuGauge', data.system.cpu_percent);
    
    // Update memory bar
    updateProgressBar('memoryBar', data.memory.percent);
    
    // Update connection counter
    document.getElementById('activeConnections').textContent = 
        data.services.vpn_processes;
    
    // Update alerts
    if (data.services.active_alerts > 0) {
        showAlertBadge(data.services.active_alerts);
    }
}