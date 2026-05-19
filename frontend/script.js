const API_BASE = "https://repo-health-intelligence.onrender.com";
let healthChart = null;

function showError(msg) {
  const el = document.getElementById("error-box");
  el.textContent = msg;
  el.style.display = "block";
}

function hideError() {
  const el = document.getElementById("error-box");
  el.textContent = "";
  el.style.display = "none";
}

function setLoading(active) {
  const btn = document.getElementById("analyzeBtn");
  const spinner = document.getElementById("loader");

  if (btn) {
    btn.disabled = active;
    btn.textContent = active ? "Analyzing..." : "Analyze";
  }

  if (spinner) {
    spinner.style.display = active ? "flex" : "none";
  }
}

function renderChart(data) {
  const labels = data.map((d) => d.date ? d.date.slice(0, 10) : d.commit.slice(0, 7));
  const healthScores = data.map((d) => d.health);
  const complexityScores = data.map((d) => d.complexity);
  const churnScores = data.map((d) => d.churn);

  const ctx = document.getElementById("healthChart").getContext("2d");

  if (healthChart) {
    healthChart.destroy();
  }

  healthChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Health",
          data: healthScores,
          borderColor: "#4caf50",
          backgroundColor: "rgba(76, 175, 80, 0.1)",
          tension: 0.3,
          fill: true,
          pointRadius: 3,
        },
        {
          label: "Complexity",
          data: complexityScores,
          borderColor: "#ff9800",
          backgroundColor: "rgba(255, 152, 0, 0.05)",
          tension: 0.3,
          fill: false,
          pointRadius: 3,
        },
        {
          label: "Churn",
          data: churnScores,
          borderColor: "#f44336",
          backgroundColor: "rgba(244, 67, 54, 0.05)",
          tension: 0.3,
          fill: false,
          pointRadius: 3,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "top" },
        tooltip: {
          callbacks: {
            title: (items) => {
              const idx = items[0].dataIndex;
              return `Commit: ${data[idx].commit.slice(0, 7)} — ${labels[idx]}`;
            },
          },
        },
      },
      scales: {
        y: {
          min: 0,
          max: 100,
          title: { display: true, text: "Score (0–100)" },
        },
        x: {
          title: { display: true, text: "Date" },
          ticks: { maxTicksLimit: 15, maxRotation: 45 },
        },
      },
    },
  });
}

function renderCommitList(data) {
  const container = document.getElementById("commitList");
  container.innerHTML = "";

  if (!data.length) {
    container.innerHTML = "<p>No commit data available.</p>";
    return;
  }

  const table = document.createElement("table");
  table.className = "commit-table";

  const thead = document.createElement("thead");
  thead.innerHTML = `
    <tr>
      <th>Commit</th>
      <th>Date</th>
      <th>Health</th>
      <th>Complexity</th>
      <th>Churn</th>
      <th>Hotspots</th>
    </tr>`;
  table.appendChild(thead);

  const tbody = document.createElement("tbody");

  data.forEach((entry) => {
    const tr = document.createElement("tr");

    const healthClass =
      entry.health >= 75 ? "good" : entry.health >= 50 ? "warn" : "bad";

    const hotspots =
      entry.hotspots && entry.hotspots.length
        ? entry.hotspots.slice(0, 3).join(", ")
        : "—";

    tr.innerHTML = `
      <td class="mono">${entry.commit.slice(0, 7)}</td>
      <td>${entry.date ? entry.date.slice(0, 10) : "—"}</td>
      <td><span class="badge ${healthClass}">${entry.health}</span></td>
      <td>${entry.complexity}</td>
      <td>${entry.churn}</td>
      <td class="hotspots" title="${entry.hotspots ? entry.hotspots.join(", ") : ""}">${hotspots}</td>
    `;
    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  container.appendChild(table);
}

function renderAlerts(data) {
  const container = document.getElementById("alerts-box");
  container.innerHTML = "";

  const allAlerts = [];
  data.forEach((entry) => {
    if (entry.alerts && entry.alerts.length) {
      entry.alerts.forEach((alert) => {
        allAlerts.push({ commit: entry.commit.slice(0, 7), date: entry.date ? entry.date.slice(0, 10) : "—", msg: alert });
      });
    }
  });

  if (!allAlerts.length) {
    container.style.display = "none";
    return;
  }

  container.style.display = "block";

  const heading = document.createElement("h3");
  heading.textContent = `⚠️ Alerts (${allAlerts.length})`;
  container.appendChild(heading);

  const ul = document.createElement("ul");
  ul.className = "alert-list";

  allAlerts.forEach((a) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="mono">${a.commit}</span> <span class="date">${a.date}</span> — ${a.msg}`;
    ul.appendChild(li);
  });

  container.appendChild(ul);
}

function renderSummary(data) {
  const container = document.getElementById("summary-text");
  if (!container) return;

  const avg = (arr) =>
    arr.length ? Math.round(arr.reduce((a, b) => a + b, 0) / arr.length) : 0;

  const avgHealth = avg(data.map((d) => d.health));
  const avgComplexity = avg(data.map((d) => d.complexity));
  const avgChurn = avg(data.map((d) => d.churn));

  const trend =
    data.length >= 2
      ? data[data.length - 1].health - data[0].health
      : 0;

  const trendLabel =
    trend > 5 ? "📈 Improving" : trend < -5 ? "📉 Declining" : "➡️ Stable";

  container.innerHTML = `
    <div class="summary-grid">
      <div class="summary-card">
        <div class="summary-value">${avgHealth}</div>
        <div class="summary-label">Avg Health</div>
      </div>
      <div class="summary-card">
        <div class="summary-value">${avgComplexity}</div>
        <div class="summary-label">Avg Complexity</div>
      </div>
      <div class="summary-card">
        <div class="summary-value">${avgChurn}</div>
        <div class="summary-label">Avg Churn</div>
      </div>
      <div class="summary-card">
        <div class="summary-value">${trendLabel}</div>
        <div class="summary-label">Health Trend</div>
      </div>
    </div>`;
}

async function analyzeRepo() {
  hideError();

  const repoUrl = document.getElementById("repoUrl").value.trim();
  if (!repoUrl) {
    showError("Please enter a GitHub repository URL.");
    return;
  }

  setLoading(true);

  try {
    const response = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: repoUrl }),
    });

    if (!response.ok) {
      let errMsg = `Server error: ${response.status}`;
      try {
        const errData = await response.json();
        if (errData.detail) errMsg = errData.detail;
      } catch (_) {}
      throw new Error(errMsg);
    }

const responseData = await response.json();

const data = responseData.commits || [];

if (!Array.isArray(data) || data.length === 0) {
    throw new Error("No commit data returned from analysis.");
}

    document.getElementById("results").style.display = "block";

    renderSummary(data);
    renderChart(data);
    renderCommitList(data);
    renderAlerts(data);

  } catch (err) {
    showError(err.message || "An unexpected error occurred.");
    document.getElementById("results").style.display = "none";
  } finally {
    setLoading(false);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("analyzeBtn");
  if (btn) btn.addEventListener("click", analyzeRepo);

  const input = document.getElementById("repoUrl");
  if (input) {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") analyzeRepo();
    });
  }

  const alertsBox = document.getElementById("alerts-box");
  if (alertsBox) alertsBox.style.display = "none";

  const resultsSection = document.getElementById("results");
  if (resultsSection) resultsSection.style.display = "none";
});

window.analyze = analyzeRepo;