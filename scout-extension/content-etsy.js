// Scout Companion — Etsy content script
// Detects page type and extracts data accordingly.

(function() {
  const url = window.location.href;

  // ── Search results page ───────────────────────────────────────
  if (url.includes("/search?")) {
    waitForSelector(".v2-listing-card, [data-listing-card]", () => {
      const listings = [];
      const cards = document.querySelectorAll(".v2-listing-card, [data-listing-card]");
      cards.forEach(card => {
        const titleEl = card.querySelector("h3, .v2-listing-card__title, [data-node-type='title']");
        const priceEl = card.querySelector(".currency-value, .currency-value span, .lc-price");
        const sellerEl = card.querySelector(".v2-listing-card__shop-name, a[href*='/shop/']");
        const reviewEl = card.querySelector(".star-rating, [data-rating]");
        listings.push({
          title: titleEl ? titleEl.innerText.trim() : "",
          price: priceEl ? parseFloat(priceEl.innerText.replace(/[^0-9.]/g, "")) : 0,
          seller: sellerEl ? sellerEl.innerText.trim() : "",
          reviews_count: reviewEl ? parseInt(reviewEl.getAttribute("data-rating") || "0") : 0,
          url: window.location.href,
        });
      });
      const countEl = document.querySelector("[data-search-results-count], .search-results-count");
      const total = countEl ? parseInt(countEl.innerText.replace(/[^0-9]/g, "")) : 0;
      chrome.runtime.sendMessage({ action: "scout_data", data: { listings, total_results: total } });
    });
    return;
  }

  // ── Homepage (trending / featured) ─────────────────────────────
  waitForSelector(".listing-card, .js-merch-stash-check-listing, .wt-card", () => {
    const items = [];
    const cards = document.querySelectorAll(".listing-card, .js-merch-stash-check-listing, [data-listing-id]");
    cards.forEach(card => {
      const titleEl = card.querySelector("h3, .wt-text-truncate, .listing-title");
      const priceEl = card.querySelector(".currency-value, .wt-text-title-01");
      if (titleEl) {
        items.push({
          title: titleEl.innerText.trim(),
          price: priceEl ? parseFloat(priceEl.innerText.replace(/[^0-9.]/g, "")) : 0,
          source: "etsy_home",
        });
      }
    });
    if (items.length > 0) {
      chrome.runtime.sendMessage({ action: "scout_data", data: { listings: items, total_results: items.length } });
    }
  });

  // ── Helper ────────────────────────────────────────────────────
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
