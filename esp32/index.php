<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MediMate — Patients</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            background: #0f172a;
            font-family: Arial, sans-serif;
            color: white;
            min-height: 100vh;
            padding: 40px 32px;
        }

        header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 40px;
        }

        header h1 {
            font-size: 28px;
        }

        header span {
            font-size: 14px;
            color: #94a3b8;
        }

        #content {
            display: flex;
            flex-direction: column;
            gap: 32px;
            width: 100%;
            align-items: center;
        }

        /* ---- List ---- */
        #patientGrid {
            display: flex;
            flex-direction: column;
            gap: 16px;
            max-width: 720px;
            width: 100%;
        }

        /* ---- Card ---- */
        .card {
            background: #1e293b;
            border-radius: 16px;
            padding: 20px 24px;
            display: flex;
            width: 100%;
            align-items: center;
            gap: 20px;
            transition: background 0.15s, box-shadow 0.15s;
            text-decoration: none;
            color: inherit;
        }

        .card:hover {
            background: #263448;
            box-shadow: 0 4px 16px rgba(0,0,0,0.3);
        }

        .card img {
            width: 56px;
            height: 56px;
            border-radius: 50%;
            object-fit: cover;
            flex-shrink: 0;
        }

        .card-body {
            flex: 1;
            min-width: 0;
        }

        .card-body h2 {
            font-size: 16px;
            margin-bottom: 3px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .card-body .sub {
            font-size: 13px;
            color: #94a3b8;
            margin-bottom: 8px;
        }

        .badge {
            display: inline-block;
            background: #0f172a;
            border: 1px solid #334155;
            color: #cbd5e1;
            font-size: 11px;
            padding: 3px 10px;
            border-radius: 20px;
        }

        .card-dates {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 4px;
            flex-shrink: 0;
            font-size: 12px;
            color: #64748b;
            text-align: right;
        }

        .card-dates .date-val {
            color: #94a3b8;
        }

        .card-arrow {
            color: #334155;
            font-size: 18px;
            flex-shrink: 0;
        }

        @media (max-width: 480px) {
            .card-dates { display: none; }
            body { padding: 20px 16px; }
        }

        /* ---- Search ---- */
        .search-row {
            display: flex;
            gap: 8px;
            max-width: 720px;
            width: 100%;
        }

        .search-row input {
            flex: 1;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 10px 16px;
            color: white;
            font-size: 14px;
            outline: none;
            transition: border-color 0.15s;
        }

        .search-row input::placeholder { color: #475569; }
        .search-row input:focus { border-color: #22c55e; }

        .search-row button {
            background: #22c55e;
            border: none;
            border-radius: 10px;
            padding: 10px 20px;
            color: #0f172a;
            font-weight: bold;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.15s;
            white-space: nowrap;
        }

        .search-row button:hover { background: #16a34a; }

        /* ---- States ---- */
        #message {
            color: #64748b;
            font-size: 16px;
            text-align: center;
            margin-top: 80px;
        }
    </style>
</head>
<body>

<header>
    <h1>MediMate</h1>
    <span>Patient Management</span>
</header>

<div id="content">
    <div class="search-row">
        <input type="text" id="searchInput" placeholder="Search by name or diagnosis..." />
        <button onclick="search()">Search</button>
    </div>
    <div id="patientGrid"></div>
</div>

<div id="message">Loading patients...</div>

<script>
    async function loadPatients() {
        try {
            const res    = await fetch('get_data.php');
            const result = await res.json();

            const grid = document.getElementById('patientGrid');
            const msg  = document.getElementById('message');

            if (result.status !== 'success' || result.patients.length === 0) {
                msg.textContent = 'No patients found.';
                return;
            }

            msg.style.display = 'none';

            const avatarColors = ['3b82f6','8b5cf6','ec4899','f59e0b','10b981','ef4444','06b6d4','f97316','6366f1','14b8a6'];
    function avatarColor(name) {
        let hash = 0;
        for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
        return avatarColors[Math.abs(hash) % avatarColors.length];
    }

    result.patients.forEach(p => {
                const admitted = p.admitted_date
                    ? new Date(p.admitted_date).toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric' })
                    : '—';
                const release = p.release_date
                    ? new Date(p.release_date).toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric' })
                    : 'In care';
                const avatar = p.image || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(p.name) + '&background=' + avatarColor(p.name) + '&color=ffffff&bold=true&size=128';
                const sub = [p.age ? p.age + ' yrs' : '', p.gender].filter(Boolean).join(' · ');

                const card = document.createElement('a');
                card.className = 'card';
                card.href = 'profile.php?id=' + p.id;
                card.innerHTML = `
                    <img src="${avatar}" alt="${p.name}">
                    <div class="card-body">
                        <h2>${p.name}</h2>
                        <div class="sub">${sub}</div>
                        <span class="badge">${p.diagnosis || 'No diagnosis'}</span>
                    </div>
                    <div class="card-dates">
                        <span>Admitted</span>
                        <span class="date-val">${admitted}</span>
                        <span style="margin-top:6px;">Release</span>
                        <span class="date-val">${release}</span>
                    </div>
                    <span class="card-arrow">›</span>
                `;
                grid.appendChild(card);
            });

        } catch (e) {
            document.getElementById('message').textContent = 'Error loading patients.';
            console.error(e);
        }
    }

    function search() {
        const query = document.getElementById('searchInput').value.trim().toLowerCase();
        document.querySelectorAll('#patientGrid .card').forEach(card => {
            const text = card.textContent.toLowerCase();
            card.style.display = text.includes(query) ? 'flex' : 'none';
        });
    }

    document.getElementById('searchInput').addEventListener('keydown', e => {
        if (e.key === 'Enter') search();
    });

    loadPatients();
</script>

</body>
</html>
