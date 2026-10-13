document.addEventListener('DOMContentLoaded', () => {
    const element = (tag, className, text) => {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    };

    const strengthInput = document.getElementById('watermark-strength');
    const strengthValue = document.querySelector('.strength-value');
    if (strengthInput && strengthValue) {
        strengthInput.addEventListener('input', () => {
            strengthValue.textContent = Number(strengthInput.value).toFixed(2);
        });
    }

    const appendImage = (parent, label, url) => {
        if (!url) return;
        const figure = element('figure', 'col-md-6');
        figure.append(element('figcaption', 'fw-semibold mb-2', label));
        const image = element('img', 'img-fluid rounded border');
        image.src = url;
        image.alt = label;
        figure.append(image);
        parent.append(figure);
    };

    const appendMetrics = (parent, values) => {
        const list = element('dl', 'row mt-3');
        Object.entries(values).forEach(([label, value]) => {
            if (value === undefined || value === null) return;
            list.append(element('dt', 'col-sm-4', label));
            list.append(element('dd', 'col-sm-8', String(value)));
        });
        parent.append(list);
    };

    const appendDownload = (parent, url, label) => {
        if (!url) return;
        const link = element('a', 'btn btn-sm btn-primary mt-2', label);
        link.href = url;
        parent.append(link);
    };

    const renderComparison = (status, title, leftLabel, leftUrl, rightLabel, rightUrl, metrics, downloadUrl) => {
        const panel = element('div', 'status-box result-comparison');
        panel.append(element('h5', '', title));
        const row = element('div', 'row g-3');
        appendImage(row, leftLabel, leftUrl);
        appendImage(row, rightLabel, rightUrl);
        panel.append(row);
        if (metrics) appendMetrics(panel, metrics);
        appendDownload(panel, downloadUrl, 'Download output');
        status.replaceChildren(panel);
    };

    const attackSpecs = (form) => {
        const specs = [];
        const values = {
            jpeg: 'quality',
            gaussian_noise: 'variance',
            salt_pepper: 'density',
            gaussian_blur: 'kernel_size',
            resize: 'scale',
            brightness: 'delta',
            contrast: 'factor',
            crop: 'crop_ratio'
        };
        form.querySelectorAll('.attack-choice:checked').forEach((choice) => {
            const input = form.querySelector(`.attack-strength[data-attack="${choice.value}"]`);
            if (!input || !input.value.trim()) return;
            if (choice.value === 'jpeg') {
                input.value.split(',').map((entry) => entry.trim()).filter(Boolean).forEach((entry) => {
                    specs.push({ name: choice.value, [values[choice.value]]: Number(entry) });
                });
            } else {
                specs.push({ name: choice.value, [values[choice.value]]: Number(input.value) });
            }
        });
        return specs;
    };

    const renderExperiments = (status, data) => {
        const panel = element('div', 'table-responsive experiment-table');
        const table = element('table', 'table table-hover align-middle');
        const header = element('thead');
        const heading = element('tr');
        ['Attack', 'Result', 'PSNR (dB)', 'SSIM', 'NC', 'BER', 'Time (ms)'].forEach((value) => {
            heading.append(element('th', '', value));
        });
        header.append(heading);
        table.append(header);
        const body = element('tbody');
        (data.attacks || []).forEach((result) => {
            const row = element('tr');
            const rowValues = [
                `${result.attack} ${Object.entries(result.attack_params || {})
                    .filter(([key]) => key !== 'name')
                    .map(([key, value]) => `${key}: ${value}`)
                    .join(', ')}`,
                result.psnr?.toFixed(3) ?? '—',
                result.ssim?.toFixed(5) ?? '—',
                result.nc?.toFixed(5) ?? '—',
                result.ber?.toFixed(5) ?? '—',
                result.extraction_time_ms?.toFixed(2) ?? '—'
            ];
            const attackCell = element('td', 'fw-semibold', rowValues[0]);
            row.append(attackCell);
            const statusCell = element('td');
            const badge = element('span', `result-status ${result.status || 'extraction_failed'}`, result.status || 'unavailable');
            statusCell.append(badge);
            row.append(statusCell);
            rowValues.slice(1).forEach((value) => row.append(element('td', '', value)));
            body.append(row);
            if (result.error) {
                const errorRow = element('tr');
                const errorCell = element('td', 'text-danger', `Extraction unavailable: ${result.error}`);
                errorCell.colSpan = 7;
                errorRow.append(errorCell);
                body.append(errorRow);
            }
            if (result.attacked_preview_url) {
                const imageRow = element('tr');
                const imageCell = element('td');
                imageCell.colSpan = 7;
                appendImage(imageCell, `${result.attack} attacked image`, result.attacked_preview_url);
                imageRow.append(imageCell);
                body.append(imageRow);
            }
        });
        table.append(body);
        panel.append(table);
        if (!document.getElementById('results-table') || status.id !== 'results-table') {
            const link = element('a', 'btn btn-outline-primary mt-3', 'Open results dashboard and CSV export');
            link.href = '/results';
            panel.append(link);
        }
        status.replaceChildren(panel);
    };

    const formHandlers = [
        {
            formId: 'embed-form',
            url: '/api/embed',
            statusId: 'embed-status',
            render: (status, data) => renderComparison(
                status,
                data.settings?.watermark_resized
                    ? 'Watermark embedded at reduced resolution'
                    : 'Watermark embedded',
                'Original cover',
                data.cover_preview_url,
                'Watermarked cover',
                data.watermarked_preview_url,
                {
                    ...data.metrics,
                    'Source watermark dimensions': data.settings?.source_watermark_shape?.join(' × '),
                    'Embedded watermark dimensions': data.settings?.embedded_watermark_shape?.join(' × '),
                    'Available watermark capacity': data.settings?.watermark_capacity
                },
                data.download_url
            )
        },
        {
            formId: 'extract-form',
            url: '/api/extract',
            statusId: 'extract-status',
            render: (status, data) => renderComparison(
                status,
                data.settings?.watermark_resized
                    ? 'Non-blind extraction (upscaled from reduced embedded resolution)'
                    : 'Non-blind extraction',
                'Reference watermark',
                data.reference_preview_url,
                'Extracted watermark',
                data.extracted_preview_url,
                {
                    NC: data.nc,
                    BER: data.ber,
                    'Extraction time (ms)': data.extraction_time_ms,
                    'Source watermark dimensions': data.settings?.source_watermark_shape?.join(' × '),
                    'Compared payload dimensions': data.settings?.embedded_watermark_shape?.join(' × '),
                    'Capacity fit applied': data.settings?.watermark_resized ? 'Yes; fine detail was reduced' : 'No'
                },
                data.download_url
            )
        },
        {
            formId: 'robustness-form',
            url: '/api/robustness',
            statusId: 'robustness-status',
            render: renderExperiments
        }
    ];

    formHandlers.forEach(({ formId, url, statusId, render }) => {
        const form = document.getElementById(formId);
        if (!form) return;
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const status = document.getElementById(statusId);
            const submitButton = form.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            status.replaceChildren(element('div', 'status-box', 'Processing request…'));
            try {
                const formData = new FormData(form);
                if (formId === 'robustness-form') {
                    const attacks = attackSpecs(form);
                    if (!attacks.length) throw new Error('Select at least one attack and enter its strength.');
                    formData.set('attacks', JSON.stringify(attacks));
                }
                const response = await fetch(url, { method: 'POST', body: formData });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Request failed.');
                render(status, data);
            } catch (error) {
                status.replaceChildren(element('div', 'status-box text-danger', error.message));
            } finally {
                submitButton.disabled = false;
            }
        });
    });

    const attacks = window.resultData?.attacks || [];
    const emptyState = document.getElementById('results-empty');
    const resultsContent = document.getElementById('results-content');
    if (emptyState && resultsContent) {
        if (attacks.length) {
            emptyState.classList.add('d-none');
            resultsContent.classList.remove('d-none');
            const measured = attacks.filter((item) => item.status === 'measured' && Number.isFinite(item.nc) && Number.isFinite(item.ber));
            document.getElementById('summary-total').textContent = attacks.length;
            document.getElementById('summary-measured').textContent = `${measured.length} / ${attacks.length}`;
            document.getElementById('summary-nc').textContent = measured.length
                ? (measured.reduce((sum, item) => sum + item.nc, 0) / measured.length).toFixed(3)
                : '—';
            document.getElementById('summary-ber').textContent = measured.length
                ? (measured.reduce((sum, item) => sum + item.ber, 0) / measured.length).toFixed(3)
                : '—';

            renderExperiments(document.getElementById('results-table'), { attacks });

            const measuredCount = measured.length;
            const unavailableCount = attacks.length - measuredCount;
            new Chart(document.getElementById('statusChart'), {
                type: 'doughnut',
                data: {
                    labels: ['Metrics available', 'Extraction unavailable'],
                    datasets: [{
                        data: [measuredCount, unavailableCount],
                        backgroundColor: ['#78978f', '#8d7770'],
                        borderColor: '#ffffff',
                        borderWidth: 4,
                        hoverOffset: 7
                    }]
                },
                options: {
                    maintainAspectRatio: false,
                    cutout: '66%',
                    plugins: {
                        legend: { position: 'bottom', labels: { color: '#b8c4cb', usePointStyle: true, padding: 18 } },
                        tooltip: { callbacks: { label: (context) => `${context.label}: ${context.raw}` } }
                    }
                }
            });

            if (measured.length) {
                const labels = measured.map((item) => {
                    const params = Object.entries(item.attack_params || {})
                        .filter(([key]) => key !== 'name')
                        .map(([, value]) => value)
                        .join(', ');
                    return `${item.attack}${params ? ` (${params})` : ''}`;
                });
                new Chart(document.getElementById('recoveryChart'), {
                    type: 'bar',
                    data: {
                        labels,
                        datasets: [
                            { label: 'NC', data: measured.map((item) => item.nc), backgroundColor: '#86a99e', borderRadius: 5 },
                            { label: 'BER', data: measured.map((item) => item.ber), backgroundColor: '#a68b78', borderRadius: 5 }
                        ]
                    },
                    options: {
                        maintainAspectRatio: false,
                        scales: {
                            x: { grid: { display: false }, ticks: { color: '#aebbc4', maxRotation: 35, minRotation: 0 } },
                            y: { min: 0, max: 1, grid: { color: '#36434d' }, ticks: { color: '#aebbc4' } }
                        },
                        plugins: {
                            legend: { position: 'bottom', labels: { color: '#b8c4cb', usePointStyle: true, padding: 18 } },
                            tooltip: { mode: 'index', intersect: false }
                        }
                    }
                });
            } else {
                document.getElementById('recoveryChart').replaceWith(
                    element('p', 'empty-state', 'No valid NC or BER measurements are available to chart.')
                );
            }
        } else {
            resultsContent.classList.add('d-none');
            emptyState.classList.remove('d-none');
        }
    }
});
