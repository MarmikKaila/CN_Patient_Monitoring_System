const statusEl = document.getElementById('status');
const patientsBody = document.getElementById('patients-body');
const alertsList = document.getElementById('alerts');

const udpPortEl = document.getElementById('udp-port');
const tcpPortEl = document.getElementById('tcp-port');
const wsPortEl = document.getElementById('ws-port');
const udpCountEl = document.getElementById('udp-count');
const tcpCountEl = document.getElementById('tcp-count');

const chartsContainer = document.getElementById('charts-container');
const charts = new Map();  // patientId -> Chart instance
const maxPoints = 30;

const patients = new Map();

let udpPacketsReceived = 0;
let tcpConnections = 0;

function wsUrl() {
  const proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
  return proto + location.host + '/ws';
}

function formatTs(ts) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString();
}

function renderPatients() {
  const rows = [];
  for (const [id, t] of Array.from(patients.entries()).sort()) {
    const v = t.vitals;
    rows.push(`<tr>
      <td>${id}</td>
      <td>${v.heart_rate} bpm</td>
      <td>${v.spo2.toFixed ? v.spo2.toFixed(1) : v.spo2}%</td>
      <td>${v.blood_pressure_sys}/${v.blood_pressure_dia}</td>
      <td>${v.temperature.toFixed ? v.temperature.toFixed(1) : v.temperature} °C</td>
      <td>${v.respiration_rate}/min</td>
      <td>${formatTs(t.timestamp)}</td>
    </tr>`);
  }
  patientsBody.innerHTML = rows.join('\n');
}

function addAlert(a) {
  const li = document.createElement('li');
  li.className = `sev-${a.severity}`;
  li.textContent = `[${new Date(a.timestamp * 1000).toLocaleTimeString()}] ${a.patient_id}: ${a.type} (${a.severity}) - ${a.message}`;
  alertsList.prepend(li);
  updateCNInfo();
}

function updateCNInfo(cnInfo = {}) {
  udpPortEl.textContent = cnInfo.udp_port || udpPortEl.textContent || 'N/A';
  tcpPortEl.textContent = cnInfo.tcp_port || tcpPortEl.textContent || 'N/A';
  wsPortEl.textContent = cnInfo.ws_port || wsPortEl.textContent || 'N/A';
  udpCountEl.textContent = udpPacketsReceived;
  tcpCountEl.textContent = tcpConnections;
}

function createChart(patientId) {
  if (document.getElementById(`chart-div-${patientId}`)) {
    return charts.get(patientId);
  }

  const container = document.createElement('div');
  container.classList.add('patient-chart');
  container.id = `chart-div-${patientId}`;

  const title = document.createElement('h3');
  title.textContent = `Vitals: ${patientId}`;
  container.appendChild(title);

  const canvas = document.createElement('canvas');
  canvas.id = `chart-${patientId}`;
  container.appendChild(canvas);
  chartsContainer.appendChild(container);

  const ctx = canvas.getContext('2d');
  const chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        { label: 'Heart Rate (bpm)', borderColor: 'red', data: [], fill: false, yAxisID: 'y' },
        { label: 'SpO2 (%)', borderColor: 'blue', data: [], fill: false, yAxisID: 'y1' },
        { label: 'Systolic BP', borderColor: 'green', data: [], fill: false, yAxisID: 'y' },
        { label: 'Diastolic BP', borderColor: 'purple', data: [], fill: false, yAxisID: 'y' },
        { label: 'Temperature (°C)', borderColor: 'orange', data: [], fill: false, yAxisID: 'y1' },
        { label: 'Respiration Rate', borderColor: 'brown', data: [], fill: false, yAxisID: 'y' },
      ],
    },
    options: {
      responsive: true,
      animation: false,
      interaction: { mode: 'nearest', intersect: false },
      stacked: false,
      scales: {
        x: {
          type: 'time',
          time: {
            unit: 'second',
            displayFormats: { second: 'HH:mm:ss' },
            tooltipFormat: 'HH:mm:ss'
          },
          grid: { color: 'rgba(224,230,240,0.1)' },
          ticks: { color: '#e0e6f0' }
        },
        y: {
          type: 'linear',
          position: 'left',
          beginAtZero: true,
          suggestedMax: 200,
          grid: { color: 'rgba(224,230,240,0.1)' },
          ticks: { color: '#e0e6f0' }
        },
        y1: {
          type: 'linear',
          position: 'right',
          suggestedMin: 30,
          suggestedMax: 110,
          grid: {
            drawOnChartArea: false,
            color: 'rgba(224,230,240,0.1)'
          },
          ticks: { color: '#e0e6f0' }
        },
      },
      plugins: {
        legend: {
          labels: { color: '#e0e6f0' }
        }
      }
    },
  });

  charts.set(patientId, chart);
  return chart;
}

function updateChart(patientId, vitals, timestamp) {
  let chart = charts.get(patientId);
  if (!chart) {
    chart = createChart(patientId);
  }

  const timeLabel = new Date(timestamp * 1000);
  chart.data.labels.push(timeLabel);
  chart.data.datasets[0].data.push(vitals.heart_rate);
  chart.data.datasets[1].data.push(vitals.spo2);
  chart.data.datasets[2].data.push(vitals.blood_pressure_sys);
  chart.data.datasets[3].data.push(vitals.blood_pressure_dia);
  chart.data.datasets[4].data.push(vitals.temperature);
  chart.data.datasets[5].data.push(vitals.respiration_rate);

  if (chart.data.labels.length > maxPoints) {
    chart.data.labels.shift();
    chart.data.datasets.forEach(ds => ds.data.shift());
  }

  chart.update('none');
}

function handleMessage(msg) {
  if (msg.type === 'snapshot') {
    const st = msg.data;
    patients.clear();
    for (const [id, t] of Object.entries(st.patients)) {
      patients.set(id, t);
    }
    for (const a of st.alerts || []) {
      addAlert(a);
    }
    renderPatients();
    updateCNInfo(st.cn_info || {});
    return;
  }

  if (msg.type === 'telemetry') {
    const t = msg.data;
    patients.set(t.patient_id, t);
    udpPacketsReceived++;
    renderPatients();
    updateChart(t.patient_id, t.vitals, t.timestamp);
    updateCNInfo();
    return;
  }

  if (msg.type === 'alert') {
    addAlert(msg.data);

    const patientId = msg.data.patient_id;
    const vitals = msg.data.vitals;   // ✅ vitals come directly from alert now
    const timestamp = msg.data.timestamp;

    if (vitals) {
      patients.set(patientId, { vitals, timestamp });
      renderPatients();
      updateChart(patientId, vitals, timestamp);
    }
    return;
  }

  if (msg.type === 'cn_stats') {
    tcpConnections = msg.data.tcp_connections || tcpConnections;
    updateCNInfo(msg.data);
  }
}

function connect() {
  const ws = new WebSocket(wsUrl());
  
  ws.onopen = () => {
    statusEl.textContent = 'Connected';
  };

  ws.onmessage = (ev) => {
    if (ev.data === '\n') return;
    try {
      handleMessage(JSON.parse(ev.data));
    } catch (error) {
      console.error('Failed to parse message:', error);
    }
  };

  ws.onclose = () => {
    statusEl.textContent = 'Disconnected. Reconnecting...';
    setTimeout(connect, 1000);
  };

  ws.onerror = () => {
    ws.close();
  };
}

connect();
