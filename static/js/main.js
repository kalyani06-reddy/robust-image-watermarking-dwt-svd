document.addEventListener('DOMContentLoaded', () => {
    const handleSubmit = async (formId, url, statusId) => {
        const form = document.getElementById(formId);
        if (!form) return;
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const status = document.getElementById(statusId);
            const submitButton = form.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            status.innerHTML = '<div class="status-box">Processing request…</div>';
            try {
                const formData = new FormData(form);
                const response = await fetch(url, { method: 'POST', body: formData });
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || 'Request failed');
                }
                status.innerHTML = `
                    <div class="status-box">
                        <strong>Success.</strong> ${JSON.stringify(data, null, 2)}
                        ${data.download_url ? `<br><a href="${data.download_url}" class="btn btn-sm btn-primary mt-2">Download</a>` : ''}
                    </div>
                `;
            } catch (error) {
                status.innerHTML = `<div class="status-box text-danger">${error.message}</div>`;
            } finally {
                submitButton.disabled = false;
            }
        });
    };

    handleSubmit('embed-form', '/api/embed', 'embed-status');
    handleSubmit('extract-form', '/api/extract', 'extract-status');
    handleSubmit('robustness-form', '/api/robustness', 'robustness-status');

    if (window.resultData && window.resultData.attacks) {
        const attacks = window.resultData.attacks || [];
        const labels = attacks.map((item) => item.attack || 'Attack');
        const ncData = attacks.map((item) => Number(item.nc || 0));
        const berData = attacks.map((item) => Number(item.ber || 0));

        new Chart(document.getElementById('ncChart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Normalized Correlation (NC)',
                    data: ncData,
                    backgroundColor: '#2563eb'
                }]
            },
            options: { responsive: true }
        });

        new Chart(document.getElementById('berChart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Bit Error Rate (BER)',
                    data: berData,
                    backgroundColor: '#7c3aed'
                }]
            },
            options: { responsive: true }
        });

        const table = document.getElementById('results-table');
        table.innerHTML = `
            <table>
                <thead>
                    <tr><th>Attack</th><th>NC</th><th>BER</th><th>Time (ms)</th></tr>
                </thead>
                <tbody>
                    ${attacks.map(item => `
                        <tr>
                            <td>${item.attack}</td>
                            <td>${Number(item.nc || 0).toFixed(4)}</td>
                            <td>${Number(item.ber || 0).toFixed(4)}</td>
                            <td>${Number(item.extraction_time_ms || 0).toFixed(2)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }
});
