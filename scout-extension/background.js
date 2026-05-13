// Scout Companion — Background Service Worker (MV3)
// Polls the local Python bridge for commands, executes them via browser tabs,
// and posts results back.

const BRIDGE_URL = "http://localhost:8765";
const POLL_INTERVAL_SECONDS = 2;
const TAB_TIMEOUT_MS = 25000; // 25 seconds per command tab
const MAX_CONCURRENT_TABS = 4;

// Track active tab commands so we don't open duplicates
const activeCommands = new Map(); // commandId -> {tabId, action, url}

// ── Startup: begin polling ──────────────────────────────────────
chrome.runtime.onStartup.addListener(() => {
  startPolling();
});
chrome.runtime.onInstalled.addListener(() => {
  startPolling();
});

function startPolling() {
  chrome.alarms.create("poll-commands", { periodInMinutes: POLL_INTERVAL_SECONDS / 60 });
}

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "poll-commands") {
    pollCommands();
  }
});

// ── Poll bridge for pending commands ────────────────────────────
async function pollCommands() {
  try {
    const resp = await fetch(`${BRIDGE_URL}/api/commands`);
    if (!resp.ok) return;
    const commands = await resp.json();
    if (!Array.isArray(commands) || commands.length === 0) return;

    for (const cmd of commands) {
      if (activeCommands.size >= MAX_CONCURRENT_TABS) break;
      if (activeCommands.has(cmd.id)) continue;
      dispatchCommand(cmd);
    }
  } catch (err) {
    // Bridge not reachable — silent
  }
}

// ── Dispatch a command ──────────────────────────────────────────
async function dispatchCommand(cmd) {
  const { id, action, params } = cmd;

  switch (action) {
    case "search_etsy":
      return openAndScrape(id, action, buildEtsyUrl(params), "etsy");
    case "etsy_trending":
      return openAndScrape(id, action, "https://www.etsy.com/", "etsy-trending");
    case "search_redbubble":
      return openAndScrape(id, action, buildRedbubbleUrl(params), "redbubble");
    case "redbubble_popular":
      return openAndScrape(id, action, "https://www.redbubble.com/shop/popular", "redbubble-popular");
    case "search_spreadshirt":
      return openAndScrape(id, action, buildSpreadshirtUrl(params), "spreadshirt");
    case "spreadshirt_trending":
      return openAndScrape(id, action, "https://www.spreadshirt.com/shop/designs?q=trending", "spreadshirt");
    case "search_pinterest":
      return openAndScrape(id, action, buildPinterestUrl(params), "pinterest");
    case "pinterest_trending":
      return openAndScrape(id, action, "https://www.pinterest.com/ideas/trending/", "pinterest-trending");
    case "get_bsr":
      return openAndScrape(id, action, buildAmazonDpUrl(params), "amazon-product");
    case "search_amazon":
      return openAndScrape(id, action, buildAmazonSearchUrl(params), "amazon-search");
    case "amazon_bestsellers":
      return openAndScrape(id, action, "https://www.amazon.com/gp/bestsellers/fashion/", "amazon-bestsellers");
    case "amazon_movers":
      return openAndScrape(id, action, "https://www.amazon.com/gp/movers-and-shakers/fashion/", "amazon-movers");
    case "get_google_suggest":
      return fetchGoogleSuggest(id, params);
    default:
      postResult(id, { status: "error", error: `Unknown action: ${action}` });
  }
}

// ── Open tab, wait for content script, post result ──────────────
function openAndScrape(commandId, action, url, pageType) {
  return new Promise((resolve) => {
    chrome.tabs.create({ url, active: false }, (tab) => {
      activeCommands.set(commandId, { tabId: tab.id, action, url });

      // Timeout guard
      const timeout = setTimeout(() => {
        if (activeCommands.has(commandId)) {
          postResult(commandId, { status: "error", error: "tab_timeout" });
          cleanupTab(commandId, tab.id);
          resolve();
        }
      }, TAB_TIMEOUT_MS);

      // Listen for result from content script
      const listener = (message, sender) => {
        if (sender.tab && sender.tab.id === tab.id &&
            message.action === "scout_data") {
          clearTimeout(timeout);
          postResult(commandId, { status: "success", data: message.data });
          cleanupTab(commandId, tab.id);
          chrome.runtime.onMessage.removeListener(listener);
          resolve();
        }
      };
      chrome.runtime.onMessage.addListener(listener);

      // Also detect tab crash / close
      const removeListener = (closedTabId) => {
        if (closedTabId === tab.id && activeCommands.has(commandId)) {
          clearTimeout(timeout);
          postResult(commandId, { status: "error", error: "tab_closed" });
          activeCommands.delete(commandId);
          chrome.runtime.onMessage.removeListener(listener);
          chrome.tabs.onRemoved.removeListener(removeListener);
          resolve();
        }
      };
      chrome.tabs.onRemoved.addListener(removeListener);
    });
  });
}

function cleanupTab(commandId, tabId) {
  activeCommands.delete(commandId);
  try { chrome.tabs.remove(tabId); } catch (_) {}
}

// ── Google Suggest (no content script needed) ───────────────────
async function fetchGoogleSuggest(commandId, params) {
  const query = (params.query || "").trim();
  if (!query) {
    return postResult(commandId, { status: "error", error: "empty_query" });
  }
  try {
    const url = `https://www.google.com/complete/search?q=${encodeURIComponent(query)}&client=firefox`;
    const resp = await fetch(url);
    const text = await resp.text();
    // Google returns JSONP:  window.google.ac.h([...])
    const jsonStr = text.replace(/^window\.google\.ac\.h\(/, "").replace(/\)$/,"");
    const data = JSON.parse(jsonStr);
    const suggestions = (Array.isArray(data) && data.length >= 2 && Array.isArray(data[1]))
      ? data[1].map(s => Array.isArray(s) ? String(s[0]) : String(s))
      : [];
    postResult(commandId, {
      status: "success",
      data: { suggestions, query },
    });
  } catch (err) {
    postResult(commandId, { status: "error", error: err.message });
  }
}

// ── Post result back to bridge ──────────────────────────────────
async function postResult(commandId, payload) {
  try {
    await fetch(`${BRIDGE_URL}/api/result/${commandId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (_) {}
}

// ── URL builders ────────────────────────────────────────────────
function buildEtsyUrl(params) {
  const q = encodeURIComponent(params.query || "");
  return `https://www.etsy.com/search?q=${q}&ref=search_bar`;
}

function buildRedbubbleUrl(params) {
  const q = encodeURIComponent(params.query || "");
  return `https://www.redbubble.com/shop/?query=${q}&iaCode=u-tshirts`;
}

function buildSpreadshirtUrl(params) {
  const q = encodeURIComponent(params.query || "");
  return `https://www.spreadshirt.com/shop/designs?q=${q}`;
}

function buildPinterestUrl(params) {
  const q = encodeURIComponent(params.query || "");
  return `https://www.pinterest.com/search/pins/?q=${q}`;
}

function buildAmazonDpUrl(params) {
  const asin = (params.asin || "").trim();
  return `https://www.amazon.com/dp/${asin}`;
}

function buildAmazonSearchUrl(params) {
  const q = encodeURIComponent(params.query || "");
  return `https://www.amazon.com/s?k=${q}`;
}
