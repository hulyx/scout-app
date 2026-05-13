// Scout Companion — Spreadshirt content script
// Handles: /shop/* pages (search, designs)

(function() {
  const selectors = "[data-testid='product-card'], [data-testid='design-card'], article, .product-card";
  waitForSelector(selectors, () => {
    const designs = [];
    const cards = document.querySelectorAll("[data-testid='product-card'], [data-testid='design-card'], article, .product-card, [class*='design-card']");
    cards.forEach(card => {
      const titleEl = card.querySelector("h2, h3, span[data-testid*='title'], [class*='title'], a[href*='/design/']");
      const priceEl = card.querySelector("[class*='price'], .price, span[class*='amount']");
      if (titleEl) {
        const title = (titleEl.innerText || titleEl.getAttribute("title") || "").trim();
        if (title) {
          designs.push({
            title: title,
            price: priceEl ? parseFloat(priceEl.innerText.replace(/[^0-9.,]/g, "").replace(",", ".")) : 0,
          });
        }
      }
    });
    const countEl = document.querySelector("[data-testid='result-count'], [class*='result-count'], [class*='count']");
    const total = countEl ? parseInt(countEl.innerText.replace(/[^0-9]/g, "")) : 0;
    chrome.runtime.sendMessage({ action: "scout_data", data: { designs, total_results: total || designs.length } });
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
