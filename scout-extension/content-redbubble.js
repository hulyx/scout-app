// Scout Companion — Redbubble content script
// Handles: /shop/* pages (search, popular)

(function() {
  const url = window.location.href;
  const isPopular = url.includes("/popular");

  // ── Search / Popular results ──────────────────────────────────
  const selectors = "[data-test-id='work-card'], .WorkCard, [class*='work-card'], article";
  waitForSelector(selectors, () => {
    const works = [];
    const cards = document.querySelectorAll(selectors);
    cards.forEach(card => {
      const titleEl = card.querySelector("h2, [data-test-id='work-title'], [class*='title'], a[href*='/works/']");
      const priceEl = card.querySelector("span.price, [data-test-id='price'], [class*='price']");
      const artistEl = card.querySelector("a.artist-link, [data-test-id='artist-name'], [class*='artist']");
      if (titleEl) {
        works.push({
          title: (titleEl.innerText || titleEl.getAttribute("title") || "").trim(),
          price: priceEl ? parseFloat(priceEl.innerText.replace(/[^0-9.]/g, "")) : 0,
          artist: artistEl ? (artistEl.innerText || "").trim() : "",
        });
      }
    });
    const countEl = document.querySelector("[class*='ResultCount'], .result-count");
    const total = countEl ? parseInt(countEl.innerText.replace(/[^0-9]/g, "")) : 0;
    chrome.runtime.sendMessage({ action: "scout_data", data: { works, total_results: total || works.length } });
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
