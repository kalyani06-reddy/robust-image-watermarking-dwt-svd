document.addEventListener('DOMContentLoaded', () => {
    const element = (tag, className, text) => {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    };

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
        const panel = element('div', 'status-box');
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
        const panel = element('div', 'status-box');
        panel.append(element('h5', '', 'Experiment results'));
        const table = element('table', 'table table-striped');
        const header = element('thead');
        const heading = element('tr');
        ['Attack', 'Status', 'PSNR (dB)', 'SSIM', 'NC', 'BER', 'Extraction time (ms)'].forEach((value) => {
            heading.append(element('th', '', value));
        });
        header.append(heading);
        table.append(header);
        const body = element('tbody');
        (data.attacks || []).forEach((result) => {
            const row = element('tr');
            [
                `${result.attack} ${JSON.stringify(result.attack_params || {})}`,
                result.status,
                result.psnr?.toFixed(3) ?? '—',
                result.ssim?.toFixed(5) ?? '—',
                result.nc?.toFixed(5) ?? '—',
                result.ber?.toFixed(5) ?? '—',
                result.extraction_time_ms?.toFixed(2) ?? '—'
            ].forEach((value) => row.append(element('td', '', value)));
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
        const link = element('a', 'btn btn-outline-primary', 'Open results dashboard and CSV export');
        link.href = '/results';
        panel.append(link);
        status.replaceChildren(panel);
    };

    const formHandlers = [
        {
            formId: 'embed-form',
            url: '/api/embed',
            statusId: 'embed-status',
            render: (status, data) => renderComparison(
                status,
                'Watermark embedded',
                'Original cover',
                data.cover_preview_url,
                'Watermarked cover',
                data.watermarked_preview_url,
                data.metrics,
                data.download_url
            )
        },
        {
            formId: 'extract-form',
            url: '/api/extract',
            statusId: 'extract-status',
            render: (status, data) => renderComparison(
                status,
                'Non-blind extraction',
                'Reference watermark',
                data.reference_preview_url,
                'Extracted watermark',
                data.extracted_preview_url,
                { NC: data.nc, BER: data.ber, 'Extraction time (ms)': data.extraction_time_ms },
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

    if (window.resultData && window.resultData.attacks) {
        const attacks = window.resultData.attacks;
        const valid = attacks.filter((item) => item.status === 'measured' && item.nc !== null && item.ber !== null);
        const table = document.getElementById('results-table');
        if (table) {
            const rows = attacks.map((item) => ({
                attack: `${item.attack} ${JSON.stringify(item.attack_params || {})}`,
                status: item.status,
                psnr: item.psnr,
                ssim: item.ssim,
                nc: item.nc,
                ber: item.ber,
                extraction_time_ms: item.extraction_time_ms
            }));
            renderExperiments(table, { attacks: rows });
        }
        if (valid.length) {
            const labels = valid.map((item) => `${item.attack} ${JSON.stringify(item.attack_params || {})}`);
            new Chart(document.getElementById('ncChart'), {
                type: 'bar',
                data: { labels, datasets: [{ label: 'Normalized Correlation (NC)', data: valid.map((item) => item.nc), backgroundColor: '#2563eb' }] },
                options: { responsive: true, scales: { y: { min: -1, max: 1 } } }
            });
            new Chart(document.getElementById('berChart'), {
                type: 'bar',
                data: { labels, datasets: [{ label: 'Bit Error Rate (BER)', data: valid.map((item) => item.ber), backgroundColor: '#7c3aed' }] },
                options: { responsive: true, scales: { y: { min: 0, max: 1 } } }
            });
        } else {
            const tableContainer = document.getElementById('results-table');
            tableContainer.prepend(element('p', 'text-muted', 'No valid recovery measurements are available to chart.'));
        }
    }
});
