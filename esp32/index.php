<!DOCTYPE html>
<html>

<head>

    <title>MediMate Dashboard</title>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        * {
            box-sizing: border-box;
        }

        body {

            margin: 0;
            padding: 0;
            background: #0f172a;
            font-family: Arial;
            color: white;
        }

        .container {

            width: 90%;
            max-width: 1000px;
            margin: auto;
            padding: 40px 0;
        }

        h1 {

            text-align: center;
            font-size: 50px;
            margin-bottom: 40px;
        }

        .card {

            background: #1e293b;
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
        }

        .pulse {

            text-align: center;
            font-size: 90px;
            font-weight: bold;
            color: #22c55e;
        }

        .status {

            text-align: center;
            font-size: 24px;
            margin-top: 20px;
            font-weight: bold;
        }

        .time {

            text-align: center;
            margin-top: 15px;
            color: #cbd5e1;
        }

        .chart-container {

            height: 400px;
        }

        canvas {

            background: white;
            border-radius: 15px;
            padding: 10px;
        }
    </style>

</head>

<body>

    <div class="container">

        <h1>MediMate Health Monitor</h1>

        <div class="card">

            <div style="text-align:center;font-size:28px;">
                Current Pulse
            </div>

            <div class="pulse" id="pulseValue">
                --
            </div>

            <div class="status" id="deviceStatus">
                Checking...
            </div>

            <div class="time" id="lastUpdate">
                --
            </div>

        </div>

        <div class="card">

            <div class="chart-container">

                <canvas id="pulseChart"></canvas>

            </div>

        </div>

    </div>

    <script>
        // ======================================
        // CHART
        // ======================================

        const ctx =
            document.getElementById('pulseChart');

        const chart = new Chart(ctx, {

            type: 'line',

            data: {

                labels: [],

                datasets: [{

                    label: 'Pulse Data',

                    data: [],

                    borderColor: '#22c55e',

                    backgroundColor: 'rgba(34,197,94,0.2)',

                    borderWidth: 3,

                    tension: 0.4,

                    fill: true
                }]
            },

            options: {

                responsive: true,

                maintainAspectRatio: false,

                animation: false,

                scales: {

                    y: {

                        beginAtZero: true
                    }
                }
            }
        });

        // ======================================
        // LOAD DATA
        // ======================================

        async function loadData() {

            try {

                const response =
                    await fetch('get_data.php');

                const result =
                    await response.json();

                if (result.status !== 'success')
                    return;

                const data = result.data;

                if (data.length === 0)
                    return;

                const latest =
                    data[data.length - 1];

                // ======================================
                // PULSE
                // ======================================

                document.getElementById(
                        'pulseValue'
                    ).innerText =
                    latest.pulse;

                // ======================================
                // STATUS
                // ======================================

                const statusEl =
                    document.getElementById(
                        'deviceStatus'
                    );

                if (result.device_status ===
                    'Connected') {

                    statusEl.innerHTML =
                        '🟢 Device Connected';

                    statusEl.style.color =
                        '#22c55e';

                } else {

                    statusEl.innerHTML =
                        '🔴 Device Offline';

                    statusEl.style.color =
                        '#ef4444';
                }

                // ======================================
                // TIME
                // ======================================

                document.getElementById(
                        'lastUpdate'
                    ).innerHTML =
                    'Last Update:<br>' +
                    latest.created_at;

                // ======================================
                // CHART
                // ======================================

                chart.data.labels =
                    data.map((item, index) =>
                        index + 1
                    );

                chart.data.datasets[0].data =
                    data.map(item => item.pulse);

                chart.update();

            } catch (error) {

                console.log(error);
            }
        }

        // ======================================
        // AUTO REFRESH
        // ======================================

        loadData();

        setInterval(loadData, 2000);
    </script>

</body>

</html>