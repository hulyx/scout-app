// Scout Companion — Pinterest content script
// Handles: /search/* and /ideas/* pages

(function() {
  const url = window.location.href;

  // ── Pinterest Trending / Ideas page ───────────────────────────
  if (url.includes("/ideas/")) {
    waitForSelector("[data-test-id='pin'], .PinCard, [class*='pin'], article img", () => {
      const pins = [];
      const cards = document.querySelectorAll("[data-test-id='pin'], .PinCard, [class*='pin']");
      cards.forEach(card => {
        const imgEl = card.querySelector("img");
        const titleEl = card.querySelector("[data-test-id='pin-title'], [class*='title'], a");
        const desc = imgEl?.getAttribute("alt") || titleEl?.innerText || "";
        if (desc.trim()) {
          pins.push({ title: desc.trim(), source: "pinterest_trending" });
        }
      });
      // Also try to get categories/titles from the page
      if (pins.length === 0) {
        document.querySelectorAll("img[alt]").forEach(img => {
          const alt = img.getAttribute("alt") || "";
          if (alt.length > 10 && alt.length < 200) {
            pins.push({ title: alt.trim(), source: "pinterest_trending" });
          }
        });
      }
      chrome.runtime.sendMessage({ action: "scout_data", data: { pins, total_results: pins.length } });
    });
    return;
  }

  // ── Pinterest Search page ─────────────────────────────────────
  waitForSelector("[data-test-id='pin'], .PinCard, [class*='pin']", () => {
    const pins = [];
    const cards = document.querySelectorAll("[data-test-id='pin'], .PinCard, [class*='pin'], [data-test-id='richPin']");
    cards.forEach(card => {
      const imgEl = card.querySelector("img");
      const titleEl = card.querySelector("[data-test-id='pin-title'], [class*='title']");
      const desc = imgEl?.getAttribute("alt") || titleEl?.innerText || "";
      const linkEl = card.querySelector("a");
      const href = linkEl?.getAttribute("href") || "";
      if (desc.trim()) {
        pins.push({ title: desc.trim(), url: href, source: "pinterest_search" });
      }
    });
    chrome.runtime.sendMessage({ action: "scout_data", data: { pins, total_results: pins.length } });
  });

  function waitForSelector(selector, callback, maxWait = 8000) {
    const check = () => {
      const el = document.querySelector(selector);
      if (el) return callback();
      if (Date.now() - start > maxWait) return callback();
      setTimeout(check, 300);
    };
    const start = Date.now();
    check();
  }
})();
