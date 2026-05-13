// Scout Companion — Popup Script

const BRIDGE_URL = "http://localhost:8765";
let paused = false;

document.addEventListener("DOMContentLoaded", () => {
  refreshStatus();
  document.getElementById("testBtn").addEventListener("click", testBridge);
  document.getElementById("toggleBtn").addEventListener("click", togglePause);
});

async function refreshStatus() {
  try {
    const resp = await fetch(`${BRIDGE_URL}/api/ping`);
    const data = await resp.json();
    if (data.status === "ok") {
      setOnline(true);
      updatePendingCount();
    } else {
      setOnline(false);
    }
  } catch (_) {
    setOnline(false);
  }
}

function setOnline(online) {
  const dot = document.getElementById("statusDot");
  const label = document.getElementById("bridgeStatus");
  dot.className = "status-dot " + (online ? "online" : "offline");
  label.textContent = online ? "online" : "offline";
}

async function updatePendingCount() {
  try {
    const resp = await fetch(`${BRIDGE_URL}/api/commands`);
    const commands = await resp.json();
    document.getElementById("pendingCount").textContent = Array.isArray(commands) ? commands.length : "?";
  } catch (_) {}
}

async function testBridge() {
  addLog("Testing bridge...");
  try {
    const resp = await fetch(`${BRIDGE_URL}/api/ping`);
    const data = await resp.json();
    addLog(`Bridge: ${data.status}`);
    setOnline(data.status === "ok");
  } catch (err) {
    addLog(`Bridge error: ${err.message}`);
    setOnline(false);
  }
}

function togglePause() {
  paused = !paused;
  document.getElementById("toggleBtn").textContent = paused ? "Resume" : "Pause";
  addLog(paused ? "Paused" : "Resumed");
}

function addLog(msg) {
  const area = document.getElementById("logArea");
  const div = document.createElement("div");
  div.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}
