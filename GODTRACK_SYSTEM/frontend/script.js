/**
 * GODTRACK SYSTEM CORE LOGIC
 * V8.0 Universal Core
 */

const app = {
    state: {
        laps: [],
        currentLap: 0,
        profile: 'GT3',
        timer: 0,
        interval: null,
        isRace: false,
        voice: true,
        replaySpeed: 1,
    },

    init: () => {
        console.log("GODTRACK SYSTEMS INITIALIZING...");
        app.visuals.init();
        app.charts.init();
        app.events.bind();
        app.v8.init();
        app.weather.start();
        app.engineering.load();
        app.profiles.loadList();
        app.history.load();
    },

    events: {
        bind: () => {
            // Navigation
            document.querySelectorAll('nav button').forEach(btn => {
                btn.addEventListener('click', (e) => app.ui.nav(btn));
            });
            // Tabs
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.addEventListener('click', (e) => app.ui.tab(btn));
            });
            // Sliders
            document.querySelectorAll('.eng-slider').forEach(slider => {
                const label = document.getElementById('v_' + slider.id.split('_')[1]);
                if (label) slider.addEventListener('input', (e) => label.innerText = e.target.value);
            });

            // File Upload
            const dz = document.getElementById('dropZone');
            const inp = document.getElementById('fileInput');
            if (dz && inp) {
                dz.onclick = () => inp.click();
                inp.onchange = (e) => app.upload.process(e.target.files[0]);
                dz.ondragover = (e) => { e.preventDefault(); dz.style.borderColor = 'var(--primary)'; };
                dz.ondragleave = (e) => { e.preventDefault(); dz.style.borderColor = 'var(--border)'; };
                dz.ondrop = (e) => {
                    e.preventDefault();
                    dz.style.borderColor = 'var(--border)';
                    if (e.dataTransfer.files.length) app.upload.process(e.dataTransfer.files[0]);
                }
            }
        }
    },

    session: {
        toggleTimer: () => {
            const btn = document.getElementById('btnTimer');
            if (app.state.isRace) {
                app.state.isRace = false;
                clearInterval(app.state.interval);
                btn.innerHTML = '<i class="fa-solid fa-play"></i>';
            } else {
                app.state.isRace = true;
                app.state.interval = setInterval(() => {
                    app.state.timer += 1000;
                    document.getElementById('raceTimer').innerText = new Date(app.state.timer).toISOString().substr(11, 8);
                }, 1000);
                btn.innerHTML = '<i class="fa-solid fa-pause"></i>';
            }
        },
        reset: async () => {
            if (!confirm("CONFIRM FULL SESSION RESET?")) return;
            await fetch('http://localhost:8000/api/reset');
            location.reload();
        },
        addLap: async () => {
            const tIn = document.getElementById('inTime').value;
            if (!tIn) return app.engineer.alert("NEED LAP TIME", true);

            let time = 0;
            if (tIn.includes(':')) {
                const p = tIn.split(':');
                time = (parseInt(p[0]) * 60) + parseFloat(p[1]);
            } else time = parseFloat(tIn);

            const payload = {
                lap_time: time,
                s1: parseFloat(document.getElementById('inS1').value) || time * 0.3,
                s2: parseFloat(document.getElementById('inS2').value) || time * 0.4,
                s3: parseFloat(document.getElementById('inS3').value) || time * 0.3,
                fuel_remaining: parseFloat(document.getElementById('inFuel').value) || 100,
                tyre_wear: 0
            };

            try {
                const res = await fetch('/api/lap', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
                });
                const data = await res.json();
                app.history.push(data);
                document.getElementById('inTime').value = "";
            } catch (e) { console.error(e); }
        },
        triggerPit: () => app.engineer.alert("BOX BOX BOX", true),
        toggleSC: () => app.engineer.alert("SAFETY CAR DEPLOYED", true)
    },

    history: {
        load: async () => {
            try {
                const r = await fetch('/api/laps');
                const d = await r.json();
                app.state.laps = d;
                if (d.length) {
                    app.ui.updateDashboard(d[d.length - 1]);
                    app.ui.renderTable();
                    d.forEach(l => app.charts.update(l.last_lap_time));
                }
            } catch (e) { }
        },
        push: (data) => {
            app.state.laps.push(data);
            app.ui.updateDashboard(data);
            app.ui.renderTable();
            app.charts.update(data.last_lap_time);
        }
    },

    ui: {
        nav: (btn) => {
            document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const target = btn.dataset.target;
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.getElementById(target).classList.add('active');
        },
        tab: (btn) => {
            const target = btn.dataset.tab;
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById(target).classList.add('active');
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        },
        closeTutorial: () => {
            document.getElementById('tutorialOverlay').classList.remove('active');
            app.engineer.alert("RADIO CHECK. WE ARE LIVE.");
        },
        updateDashboard: (data) => {
            document.getElementById('valFuel').innerText = data.fuel.toFixed(1) + "kg";
            document.getElementById('valFuelLaps').innerText = data.est_laps_remaining.toFixed(1) + " LAPS EST.";

            const life = Math.max(0, 100 - (data.tyre_wear * 100));
            document.getElementById('valTire').innerText = life.toFixed(0) + "%";
            document.getElementById('tireBar').style.width = life + "%";
            document.getElementById('tireBar').style.backgroundColor = life < 30 ? 'var(--secondary)' : 'var(--primary)';

            // Delta
            const dVal = document.getElementById('valDelta');
            const d = data.delta_to_best;
            dVal.innerText = (d > 0 ? "+" : "") + d.toFixed(3);
            dVal.className = d <= 0 ? "big-val txt-lime" : "big-val txt-red";

            app.engineer.alert(data.engineer_message, data.engineer_message.includes("CRITICAL") || data.engineer_message.includes("BOX"));

            document.getElementById('bestS1').innerText = data.best_s1.toFixed(3);
            document.getElementById('bestS2').innerText = data.best_s2.toFixed(3);
            document.getElementById('bestS3').innerText = data.best_s3.toFixed(3);
            document.getElementById('theoLap').innerText = data.theoretical_lap.toFixed(3);
        },
        renderTable: () => {
            const tb = document.getElementById('lapTableBody');
            tb.innerHTML = "";
            [...app.state.laps].reverse().forEach((l, i) => {
                tb.innerHTML += `<tr>
                    <td>${l.current_lap}</td>
                    <td class="txt-primary">${l.last_lap_time.toFixed(3)}</td>
                    <td>${l.s1.toFixed(1)}</td>
                    <td>${l.s2.toFixed(1)}</td>
                    <td>${l.s3.toFixed(1)}</td>
                    <td>${l.fuel.toFixed(1)}</td>
                </tr>`;
            });
        }
    },

    strategy: {
        runSim: async () => {
            const payload = {
                car_class: app.state.profile,
                initial_fuel: parseFloat(document.getElementById('simFuel').value),
                laps_to_simulate: parseInt(document.getElementById('simLaps').value),
                tyre_compound: document.getElementById('simTire').value
            };
            try {
                const r = await fetch('/api/simulate', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
                });
                const res = await r.json();

                const times = res.map(x => x.estimated_time);
                if (app.charts.sim) app.charts.sim.destroy();

                app.charts.sim = new Chart(document.getElementById('simChart'), {
                    type: 'line',
                    data: {
                        labels: res.map(x => x.lap),
                        datasets: [{
                            label: 'Pace Prediction',
                            data: times,
                            borderColor: '#ccff00',
                            backgroundColor: 'rgba(204, 255, 0, 0.1)',
                            fill: true, tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        scales: { y: { grid: { color: 'rgba(255,255,255,0.1)' } }, x: { display: false } },
                        plugins: { legend: { display: false } }
                    }
                });
                document.getElementById('simResult').style.display = 'block';
                const total = times.reduce((a, b) => a + b, 0);
                document.getElementById('simTime').innerText = (total / 60).toFixed(1) + " MIN";
            } catch (e) { }
        }
    },

    v8: {
        currentId: null,
        init: () => {
            app.v8.list();
            const dz = document.getElementById('dropZoneV8');
            const inp = document.getElementById('fileInputV8');

            if (dz && inp) {
                dz.onclick = () => inp.click();
                inp.onchange = (e) => app.v8.ingest(e.target.files[0]);
                dz.ondragover = (e) => { e.preventDefault(); dz.style.backgroundColor = 'rgba(0,240,255,0.1)'; };
                dz.ondragleave = (e) => { e.preventDefault(); dz.style.backgroundColor = 'transparent'; };
                dz.ondrop = (e) => {
                    e.preventDefault();
                    dz.style.backgroundColor = 'transparent';
                    if (e.dataTransfer.files.length) app.v8.ingest(e.dataTransfer.files[0]);
                }
            }
        },
        ingest: async (file) => {
            if (!file) return;
            const fd = new FormData();
            fd.append('file', file);
            app.engineer.alert("UNIVERSAL INGEST RUNNING...", false);
            try {
                const r = await fetch('/api/v8/ingest', { method: 'POST', body: fd });
                const d = await r.json();
                if (d.status === 'success') {
                    app.engineer.alert("PROCESS COMPLETE. SESSION SAVED.", false);
                    app.v8.list();
                    // Auto load?
                    app.v8.load(d.session_id);
                } else {
                    app.engineer.alert("INGEST FAILED: " + d.message, true);
                }
            } catch (e) { app.engineer.alert("NET ERROR", true); }
        },
        list: async () => {
            try {
                const r = await fetch('/api/v8/sessions');
                const d = await r.json();
                const cont = document.getElementById('sessionList');
                cont.innerHTML = "";
                d.forEach(s => {
                    const el = document.createElement('div');
                    el.className = 'card';
                    el.style.padding = '10px';
                    el.style.cursor = 'pointer';
                    el.style.border = '1px solid var(--border)';
                    el.innerHTML = `
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div style="font-weight:700; color:#fff;">${s.id}</div>
                            <div class="sub-val">${s.laps} LAPS</div>
                        </div>
                        <div class="sub-val" style="font-size:10px; margin-top:5px;">BEST: ${s.best.toFixed(3)} | FUEL: ${s.fuel_burn.toFixed(2)}/L</div>
                    `;
                    el.onclick = () => app.v8.load(s.id);
                    cont.appendChild(el);
                });
            } catch (e) { }
        },
        load: async (id) => {
            app.v8.currentId = id;
            try {
                const r = await fetch(`/api/v8/load/${id}`);
                const d = await r.json();
                if (d.status === 'success') {
                    app.engineer.alert(`SESSION ${id} LOADED.`);
                    // Refresh App State
                    await app.history.load(); // Reloads visual history in Dashboard

                    // Show Report
                    document.getElementById('reportPlaceholder').style.display = 'none';
                    document.getElementById('reportContent').style.display = 'block';
                    document.getElementById('reportHeader').innerText = `REPORT: ${id}`;

                    // Populate Stats
                    setTimeout(app.v8.renderReport, 500);
                }
            } catch (e) { }
        },
        renderReport: () => {
            const laps = app.state.laps;
            if (!laps.length) return;

            // Stats
            let best = 99999;
            laps.forEach(l => {
                if (l.last_lap_time < best && l.last_lap_time > 20) best = l.last_lap_time;
            });

            document.getElementById('repBest').innerText = best.toFixed(3);

            // Calc stats locally to show
            const times = laps.map(l => l.last_lap_time);
            const avg = times.reduce((a, b) => a + b, 0) / times.length;
            document.getElementById('repAvg').innerText = avg.toFixed(3);

            // Chart
            const ctx = document.getElementById('reportChart').getContext('2d');
            if (window.v8Chart) window.v8Chart.destroy();

            window.v8Chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: laps.map(l => l.current_lap),
                    datasets: [{
                        label: 'Lap Pace',
                        data: laps.map(l => l.last_lap_time),
                        borderColor: '#ccff00',
                        tension: 0.2
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { grid: { color: 'rgba(255,255,255,0.05)' } } }
                }
            });
        },
        deleteCurrent: async () => {
            if (!app.v8.currentId) return;
            if (!confirm("DELETE SESSION PERMANENTLY?")) return;
            await fetch(`/api/v8/delete/${app.v8.currentId}`, { method: 'DELETE' });
            app.v8.list();
            document.getElementById('reportPlaceholder').style.display = 'block';
            document.getElementById('reportContent').style.display = 'none';
        },
        simulateCurrent: () => {
            app.ui.nav(document.querySelector('button[data-target="strategy"]'));
        }
    },

    weather: {
        start: () => {
            setInterval(app.weather.poll, 3000);
            app.weather.render();
        },
        poll: async () => {
            try {
                const r = await fetch('/api/weather');
                const d = await r.json();
                const rec = document.getElementById('tyreRec');
                if (d.track_wetness > 0.15) {
                    rec.innerText = "WETS";
                    rec.className = "pulsing txt-primary";
                } else {
                    rec.innerText = "SLICKS";
                    rec.className = "txt-lime";
                }
            } catch (e) { }
        },
        render: () => {
            const ctx = document.getElementById('weatherRadar').getContext('2d');
            let offset = 0;
            const draw = () => {
                ctx.fillStyle = '#050505';
                ctx.fillRect(0, 0, 400, 200);

                offset = (offset + 2) % 400;

                // Draw "rain" blobs
                ctx.fillStyle = 'rgba(0, 240, 255, 0.2)';
                for (let i = 0; i < 10; i++) {
                    const x = (Date.now() / 50 + i * 50) % 450 - 25;
                    const y = Math.sin(Date.now() / 500 + i) * 50 + 100;
                    ctx.beginPath(); ctx.arc(x, y, 30, 0, Math.PI * 2); ctx.fill();
                }

                ctx.strokeStyle = '#00ff00';
                ctx.lineWidth = 2;
                ctx.beginPath(); ctx.moveTo(offset, 0); ctx.lineTo(offset, 200); ctx.stroke();
                requestAnimationFrame(draw);
            };
            draw();
        }
    },

    engineering: {
        save: async () => {
            const getVal = (id) => { const el = document.getElementById(id); return el ? parseFloat(el.value) : 0; };
            const getInt = (id) => { const el = document.getElementById(id); return el ? parseInt(el.value) : 0; };
            const getStr = (id) => { const el = document.getElementById(id); return el ? el.value : ""; };

            const setup = {
                aero: {
                    front_wing: getInt('eng_fw'),
                    rear_wing: getInt('eng_rw'),
                    splitter_map: 5, brake_ducts: 3
                },
                suspension: {
                    camber_fl: getVal('eng_camber_f'), camber_fr: getVal('eng_camber_f'),
                    camber_rl: getVal('eng_camber_r'), camber_rr: getVal('eng_camber_r'),
                    toe_front: getVal('eng_toe_f'), toe_rear: getVal('eng_toe_r'),
                    caster: getVal('eng_caster'),
                    ride_height_f: getVal('eng_rh_f'), ride_height_r: getVal('eng_rh_r'),
                    spring_f: getInt('eng_spr_f'), spring_r: getInt('eng_spr_r'),
                    arb_f: getInt('eng_arb_f'), arb_r: getInt('eng_arb_r')
                },
                drivetrain: {
                    diff_preload: getInt('eng_diff_pre'), diff_accel: getInt('eng_diff_acc'), diff_coast: getInt('eng_diff_coast'),
                    gear_ratio_final: getVal('eng_final'),
                    gear_1: getVal('eng_g1'), gear_2: getVal('eng_g2'), gear_3: getVal('eng_g3'),
                    gear_4: getVal('eng_g4'), gear_5: getVal('eng_g5'), gear_6: getVal('eng_g6'),
                    gear_7: getVal('eng_g7'), gear_8: getVal('eng_g8')
                },
                brakes: {
                    pressure: getVal('eng_brk_pres'), bias: getVal('eng_bias'),
                    disc_size_f: getInt('eng_dsk_f'), disc_size_r: getInt('eng_dsk_r'),
                    pad_compound: getInt('eng_pad')
                },
                environment: {
                    air_temp: getVal('eng_env_air'), track_temp: getVal('eng_env_trk'),
                    grip_level: getVal('eng_env_grip'), wind_speed: getVal('eng_env_wind'),
                    wind_direction: getStr('eng_env_wdir'),
                    rain_intensity: getVal('eng_env_rain')
                },
                electronics: { tc_level: getInt('eng_tc'), abs_level: getInt('eng_abs'), engine_map: 1, throttle_shape: 5 },
                tyres: { compound: 'slick_med', pressure_fl: 24.5, pressure_fr: 24.5, pressure_rl: 23.5, pressure_rr: 23.5 },
                dampers: { bump_fl: 5, bump_fr: 5, bump_rl: 5, bump_rr: 5, rebound_fl: 5, rebound_fr: 5, rebound_rl: 5, rebound_rr: 5 }
            };

            try {
                await fetch('/api/setup', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(setup)
                });
                app.engineer.alert("EXTENDED CONFIGURATION APPLIED", false);
            } catch (e) { console.error(e); }
        },
        load: async () => {
            try {
                const r = await fetch('/api/setup');
                const d = await r.json();

                const set = (id, val) => {
                    const el = document.getElementById(id);
                    if (el) {
                        el.value = val;
                        // Update linked label if exists
                        const l = document.getElementById('v_' + id.split('_')[1]);
                        if (l) l.innerText = val;
                        const l2 = document.getElementById('v_' + id.replace('eng_', '')); // Handle inconsistent naming
                        if (l2) l2.innerText = val;
                    }
                };

                // Aero
                set('eng_fw', d.aero.front_wing);
                set('eng_rw', d.aero.rear_wing);

                // Susp
                set('eng_camber_f', d.suspension.camber_fl);
                set('eng_camber_r', d.suspension.camber_rl);
                set('eng_toe_f', d.suspension.toe_front);
                set('eng_toe_r', d.suspension.toe_rear);
                set('eng_caster', d.suspension.caster);

                if (d.suspension.ride_height_f) { // Check existence for legacy setups
                    set('eng_rh_f', d.suspension.ride_height_f);
                    set('eng_rh_r', d.suspension.ride_height_r);
                    set('eng_spr_f', d.suspension.spring_f);
                    set('eng_spr_r', d.suspension.spring_r);
                    set('eng_arb_f', d.suspension.arb_f);
                    set('eng_arb_r', d.suspension.arb_r);
                }

                // Drivetrain
                if (d.drivetrain.gear_1) {
                    set('eng_diff_pre', d.drivetrain.diff_preload);
                    set('eng_diff_acc', d.drivetrain.diff_accel);
                    set('eng_diff_coast', d.drivetrain.diff_coast);
                    set('eng_final', d.drivetrain.gear_ratio_final);
                    for (let i = 1; i <= 8; i++) set(`eng_g${i}`, d.drivetrain[`gear_${i}`]);
                }

                // Brakes
                if (d.brakes) {
                    set('eng_brk_pres', d.brakes.pressure);
                    set('eng_bias', d.brakes.bias);
                    set('eng_dsk_f', d.brakes.disc_size_f);
                    set('eng_dsk_r', d.brakes.disc_size_r);
                    set('eng_pad', d.brakes.pad_compound);
                }

                // Env
                if (d.environment) {
                    set('eng_env_air', d.environment.air_temp);
                    set('eng_env_trk', d.environment.track_temp);
                    set('eng_env_grip', d.environment.grip_level);
                    set('eng_env_wind', d.environment.wind_speed);
                    set('eng_env_wdir', d.environment.wind_direction);
                    set('eng_env_rain', d.environment.rain_intensity || 0);

                    // Visual Update
                    const wVal = document.getElementById('weatherState');
                    if (d.environment.rain_intensity > 80) wVal.innerText = "STORM";
                    else if (d.environment.rain_intensity > 20) wVal.innerText = "RAIN";
                    else wVal.innerText = "DRY";
                }

                set('eng_tc', d.electronics.tc_level);
                set('eng_abs', d.electronics.abs_level);
            } catch (e) { }
        }
    },

    profiles: {
        save: async () => { alert("Profile saved locally (Demoware)"); },
        loadList: async () => {
            const l = document.getElementById('profileList');
            l.innerHTML = "";
            try {
                const r = await fetch('/api/profiles');
                const d = await r.json();
                d.forEach(n => {
                    const b = document.createElement('button');
                    b.innerText = n;
                    b.className = 'btn btn-outline';
                    b.style.fontSize = '12px';
                    b.style.padding = '5px 10px';
                    b.onclick = () => app.profiles.load(n);
                    l.appendChild(b);
                });
            } catch (e) { }
        },
        load: async (n) => {
            await fetch(`/api/profiles/load/${n}`);
            app.engineering.load();
            app.engineer.alert(`PROFILE ${n} LOADED`);
        }
    },

    charts: {
        live: null, sim: null,
        init: () => {
            const ctx = document.getElementById('liveChart').getContext('2d');
            const grad = ctx.createLinearGradient(0, 0, 0, 250);
            grad.addColorStop(0, 'rgba(0, 240, 255, 0.5)');
            grad.addColorStop(1, 'rgba(0, 240, 255, 0)');

            app.charts.live = new Chart(ctx, {
                type: 'line',
                data: { labels: [], datasets: [{ data: [], borderColor: '#00f0ff', backgroundColor: grad, fill: true, tension: 0.3, pointRadius: 3 }] },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { display: false },
                        y: { grid: { color: 'rgba(255,255,255,0.05)' } }
                    }
                }
            });
        },
        update: (val) => {
            app.charts.live.data.labels.push('');
            app.charts.live.data.datasets[0].data.push(val);
            if (app.charts.live.data.datasets[0].data.length > 20) {
                app.charts.live.data.labels.shift();
                app.charts.live.data.datasets[0].data.shift();
            }
            app.charts.live.update();
        }
    },

    engineer: {
        alert: (msg, crit) => {
            const p = document.getElementById('engPanel');
            const m = document.getElementById('engMsg');
            m.innerText = msg;
            p.className = crit ? "eng-panel critical" : "eng-panel";
            if (app.state.voice) app.engineer.speak(msg);
        },
        speak: (txt) => {
            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance(txt);
                u.rate = 1.1; u.pitch = 1.0;
                window.speechSynthesis.speak(u);
            }
        }
    },

    visuals: {
        init: () => {
            const c = document.getElementById('particles');
            const ctx = c.getContext('2d');
            let w = c.width = window.innerWidth, h = c.height = window.innerHeight;
            const par = Array.from({ length: 50 }, () => ({
                x: Math.random() * w, y: Math.random() * h, v: (Math.random() * .5) + .2, s: Math.random() * 2
            }));
            const anim = () => {
                ctx.fillStyle = '#050505'; ctx.fillRect(0, 0, w, h); // Clear with bg
                ctx.fillStyle = '#00f0ff';
                par.forEach(p => {
                    p.y -= p.v;
                    if (p.y < 0) p.y = h;
                    ctx.globalAlpha = Math.random() * 0.5 + 0.1;
                    ctx.beginPath(); ctx.arc(p.x, p.y, p.s, 0, Math.PI * 2); ctx.fill();
                });
                requestAnimationFrame(anim);
            };
            anim();
        }
    }
};

window.onload = app.init;
