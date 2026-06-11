<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MediMate — Patient Profile</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            background: #0f172a;
            font-family: Arial, sans-serif;
            color: white;
            min-height: 100vh;
            padding: 32px;
        }

        /* ---- Viewport clamp ---- */
        #content, .back { max-width: 1400px; margin-left: auto; margin-right: auto; }

        /* ---- Back ---- */
        .back {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: #94a3b8;
            text-decoration: none;
            font-size: 14px;
            margin-bottom: 28px;
            transition: color 0.15s;
        }
        .back:hover { color: white; }

        /* ---- Layout ---- */
        .layout {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 24px;
            align-items: start;
        }

        /* ---- Sidebar ---- */
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .card {
            background: #1e293b;
            border-radius: 16px;
            padding: 24px;
        }

        /* Patient info card */
        .patient-card {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            gap: 12px;
        }

        .patient-card img {
            width: 96px;
            height: 96px;
            border-radius: 50%;
            object-fit: cover;
        }

        .patient-card h2 {
            font-size: 20px;
        }

        .patient-card .sub {
            font-size: 14px;
            color: #94a3b8;
        }

        .badge {
            display: inline-block;
            background: #0f172a;
            border: 1px solid #334155;
            color: #cbd5e1;
            font-size: 12px;
            padding: 4px 12px;
            border-radius: 20px;
        }

        .divider {
            width: 100%;
            border: none;
            border-top: 1px solid #334155;
        }

        .meta-list {
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .meta-row {
            display: flex;
            justify-content: space-between;
            font-size: 13px;
        }

        .meta-row .label { color: #64748b; }
        .meta-row .value { color: #e2e8f0; }

        /* BPM card */
        .bpm-card {
            text-align: center;
            margin-bottom: 16px;
        }

        .bpm-card .label {
            font-size: 13px;
            color: #94a3b8;
            margin-bottom: 8px;
        }

        .bpm-card .value {
            font-size: 64px;
            font-weight: bold;
            color: #22c55e;
            line-height: 1;
        }

        .bpm-card .unit {
            font-size: 14px;
            color: #94a3b8;
            margin-top: 4px;
        }

        /* Status card */
        .status-card {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .status-card .label {
            font-size: 13px;
            color: #94a3b8;
        }

        #deviceStatus {
            font-size: 18px;
            font-weight: bold;
        }

        #lastUpdate {
            font-size: 12px;
            color: #64748b;
        }

        /* ---- Main content ---- */
        .main {
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        .chart-wrap {
            height: 380px;
            position: relative;
        }

        .card-title {
            font-size: 15px;
            color: #94a3b8;
            margin-bottom: 16px;
        }

        /* ---- Error ---- */
        #error {
            display: none;
            color: #ef4444;
            text-align: center;
            margin-top: 80px;
            font-size: 18px;
        }

        /* ---- Tablet (≤1024px): narrow sidebar ---- */
        @media (max-width: 1024px) {
            .layout {
                grid-template-columns: 240px 1fr;
            }
        }

        /* ---- Mobile (≤768px): single column ---- */
        @media (max-width: 768px) {
            body { padding: 16px; }

            .back { margin-bottom: 20px; }

            .layout {
                grid-template-columns: 1fr;
            }

            /* Stack BPM + status side by side on mobile */
            .sidebar {
                display: grid;
                grid-template-columns: 1fr;
                gap: 12px;
            }

            .bpm-status-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
            }

            .bpm-card .value { font-size: 48px; }

            .chart-wrap { height: 260px; }

            .card { padding: 16px; }
        }

        /* ---- Small mobile (≤480px) ---- */
        @media (max-width: 480px) {
            .bpm-status-row {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>

<a class="back" href="index.php">&#8592; All Patients</a>

<div id="error">Patient not found.</div>

<div id="content" style="display:none;">
    <div class="layout">

        <!-- Sidebar -->
        <div class="sidebar">

            <div class="card patient-card">
                <img id="patientImg" src="" alt="">
                <h2 id="patientName">—</h2>
                <div class="sub" id="patientSub">—</div>
                <span class="badge" id="patientDiagnosis">—</span>
                <hr class="divider">
                <div class="meta-list">
                    <div class="meta-row">
                        <span class="label">Admitted</span>
                        <span class="value" id="admittedDate">—</span>
                    </div>
                    <div class="meta-row">
                        <span class="label">Release</span>
                        <span class="value" id="releaseDate">—</span>
                    </div>
                    <div class="meta-row">
                        <span class="label">Patient ID</span>
                        <span class="value" id="patientId">—</span>
                    </div>
                </div>
            </div>

            <div class="bpm-status-row">
                <div class="card bpm-card">
                    <div class="label">Current Pulse</div>
                    <div class="value" id="pulseValue">--</div>
                    <div class="unit">BPM</div>
                </div>

                <div class="card status-card">
                    <div class="label">Device Status</div>
                    <div id="deviceStatus">Checking...</div>
                    <div id="lastUpdate">—</div>
                </div>
            </div>

        </div>

        <!-- Main -->
        <div class="main">
            <div class="card">
                <div class="card-title">Pulse History (last 30 readings)</div>
                <div class="chart-wrap">
                    <canvas id="pulseChart"></canvas>
                </div>
            </div>
        </div>

    </div>
</div>

<script>
    const params    = new URLSearchParams(window.location.search);
    const patientId = params.get('id');
    let chart       = null;
    let pollInterval = null;

    function formatDate(str) {
        if (!str) return '—';
        return new Date(str).toLocaleDateString('en-GB', {
            day: '2-digit', month: 'short', year: 'numeric'
        });
    }

    // ======================================
    // CHART
    // ======================================

    function initChart() {
        const ctx = document.getElementById('pulseChart');
        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Pulse (BPM)',
                    data: [],
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34,197,94,0.12)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointBackgroundColor: '#22c55e'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                scales: {
                    y: {
                        min: 40,
                        max: 180,
                        grid:  { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#94a3b8' }
                    },
                    x: {
                        grid:  { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#94a3b8', maxTicksLimit: 10 }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#94a3b8' } }
                }
            }
        });
    }

    // ======================================
    // LOAD DATA
    // ======================================

    async function loadData() {
        try {
            const res    = await fetch('get_data.php?patient_id=' + patientId);
            const result = await res.json();

            if (result.status !== 'success') {
                document.getElementById('error').style.display = 'block';
                return;
            }

            const p = result.patient;
            const avatar = p.image || 'https://ui-avatars.com/api/?name='
                + encodeURIComponent(p.name)
                + '&background=334155&color=ffffff&bold=true&size=128';

            document.getElementById('patientImg').src        = avatar;
            document.getElementById('patientName').textContent     = p.name;
            document.getElementById('patientSub').textContent      = [p.age ? p.age + ' yrs' : '', p.gender].filter(Boolean).join(' · ');
            document.getElementById('patientDiagnosis').textContent = p.diagnosis || 'No diagnosis';
            document.getElementById('admittedDate').textContent     = formatDate(p.admitted_date);
            document.getElementById('releaseDate').textContent      = formatDate(p.release_date);
            document.getElementById('patientId').textContent        = '#' + String(p.id).padStart(4, '0');

            document.getElementById('content').style.display = 'block';

            // Pulse
            const data   = result.data;
            const latest = data.length > 0 ? data[data.length - 1] : null;
            document.getElementById('pulseValue').textContent = latest ? latest.pulse : '--';

            // Status
            const statusEl = document.getElementById('deviceStatus');
            if (result.device_status === 'Connected') {
                statusEl.textContent = 'Device Connected';
                statusEl.style.color = '#22c55e';
            } else {
                statusEl.textContent = 'Device Offline';
                statusEl.style.color = '#ef4444';
            }

            document.getElementById('lastUpdate').textContent =
                latest ? 'Last reading: ' + latest.created_at : '—';

            // Chart
            if (!chart) initChart();
            chart.data.labels           = data.map(item => item.created_at.slice(11, 16));
            chart.data.datasets[0].data = data.map(item => item.pulse);
            chart.update();

        } catch (e) {
            document.getElementById('error').style.display = 'block';
            console.error(e);
        }
    }

    // ======================================
    // BOOT
    // ======================================

    if (!patientId) {
        document.getElementById('error').style.display = 'block';
    } else {
        loadData();
        pollInterval = setInterval(loadData, 5000);
    }
</script>

</body>
</html>
