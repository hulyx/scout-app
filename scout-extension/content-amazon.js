// Scout Companion — Amazon content script
// Handles: /dp/* (product page), /s?* (search), /gp/bestsellers/*, /gp/movers-and-shakers/*

(function() {
  const url = window.location.href;

  // ── Best Sellers page ─────────────────────────────────────────
  if (url.includes("/gp/bestsellers/")) {
    waitForSelector("#gridItemRoot, .zg-no-numbers, [data-asin], .a-carousel-card", () => {
      const items = [];
      const seen = new Set();
      // Collect titles from multiple sources for robustness
      const sources = [
        // img alt text (most reliable)
        ...document.querySelectorAll("#gridItemRoot img[alt], .zg-no-numbers img[alt], [data-asin] img[alt]"),
        // a-link-normal with text (product links)
        ...document.querySelectorAll("#gridItemRoot a.a-link-normal, .zg-no-numbers a.a-link-normal, [data-asin] a.a-link-normal"),
        // Any title-like spans/divs inside grid items
        ...document.querySelectorAll("#gridItemRoot .p13n-sc-truncate, #gridItemRoot [class*=clamp], .zg-no-numbers [class*=clamp]"),
      ];
      function isValidProductTitle(t) {
        t = t.trim();
        if (!t || t.length < 5) return false;
        if (t.startsWith("$")) return false;
        if (/out\s+of\s+\d+(\.\d+)?\s+stars/i.test(t)) return false;
        if (/^\d+(\.\d+)?\s+out\s+of\s+5/i.test(t)) return false;
        return true;
      }

      sources.forEach(el => {
        let title = el.getAttribute("alt") || el.innerText || el.getAttribute("title") || "";
        title = title.trim();
        if (!isValidProductTitle(title)) return;
        if (seen.has(title.toLowerCase())) return;
        seen.add(title.toLowerCase());
        items.push({ title, source: "amazon_bestseller" });
      });
      // Fallback: grab any reasonably sized text inside grid items
      if (items.length < 3) {
        const fallbacks = document.querySelectorAll("#gridItemRoot, .zg-no-numbers");
        fallbacks.forEach(card => {
          const text = (card.innerText || "").trim();
          const lines = text.split("\n").map(l => l.trim()).filter(l => isValidProductTitle(l));
          if (lines.length) {
            const key = lines[0].toLowerCase();
            if (!seen.has(key)) {
              seen.add(key);
              items.push({ title: lines[0], source: "amazon_bestseller" });
            }
          }
        });
      }
      chrome.runtime.sendMessage({ action: "scout_data", data: { listings: items, total_results: items.length } });
    });
    return;
  }

  // ── Movers & Shakers page ─────────────────────────────────────
  if (url.includes("/gp/movers-and-shakers/")) {
    waitForSelector("#gridItemRoot, .zg-no-numbers, [data-asin], .a-carousel-card", () => {
      const items = [];
      const seen = new Set();
      const sources = [
        ...document.querySelectorAll("#gridItemRoot img[alt], .zg-no-numbers img[alt], [data-asin] img[alt]"),
        ...document.querySelectorAll("#gridItemRoot a.a-link-normal, .zg-no-numbers a.a-link-normal, [data-asin] a.a-link-normal"),
        ...document.querySelectorAll("#gridItemRoot .a-size-medium, #gridItemRoot [class*=clamp], .zg-no-numbers [class*=clamp]"),
      ];
      sources.forEach(el => {
        let title = el.getAttribute("alt") || el.innerText || el.getAttribute("title") || "";
        title = title.trim();
        if (!isValidProductTitle(title)) return;
        if (seen.has(title.toLowerCase())) return;
        seen.add(title.toLowerCase());
        items.push({ title, source: "amazon_mover" });
      });
      if (items.length < 3) {
        const fallbacks = document.querySelectorAll("#gridItemRoot, .zg-no-numbers");
        fallbacks.forEach(card => {
          const text = (card.innerText || "").trim();
          const lines = text.split("\n").map(l => l.trim()).filter(l => isValidProductTitle(l));
          if (lines.length) {
            const key = lines[0].toLowerCase();
            if (!seen.has(key)) {
              seen.add(key);
              items.push({ title: lines[0], source: "amazon_mover" });
            }
          }
        });
      }
      chrome.runtime.sendMessage({ action: "scout_data", data: { listings: items, total_results: items.length } });
    });
    return;
  }

  // ── Product page (BSR) ────────────────────────────────────────
  if (url.includes("/dp/")) {
    waitForSelector("#productTitle", () => {
      const titleEl = document.querySelector("#productTitle, #title, h1.a-size-large");
      const title = titleEl ? titleEl.innerText.trim() : "";
      const priceEl = document.querySelector(".a-price .a-offscreen");
      const price = priceEl ? parseFloat(priceEl.innerText.replace(/[^0-9.]/g, "")) : null;
      const asin = window.location.pathname.match(/\/dp\/([A-Z0-9]{10})/)?.[1] || "";

      let bsr = null, bsrText = "";
      const detailBullets = document.querySelector("#detailBullets_feature_div");
      if (detailBullets) {
        const lis = detailBullets.querySelectorAll("li");
        lis.forEach(li => {
          const text = li.innerText || "";
          if (text.toLowerCase().includes("best sellers rank")) {
            const m = text.match(/#(\d[\d,]*)/);
            if (m) { bsr = parseInt(m[1].replace(/,/g, "")); bsrText = text.substring(0, 200); }
          }
        });
      }
      chrome.runtime.sendMessage({ action: "scout_data", data: { asin, title, price, bsr, bsr_category: bsrText } });
    });
    return;
  }

  // ── Search results page ───────────────────────────────────────
  if (url.includes("/s?")) {
    waitForSelector("[data-asin]", () => {
      const listings = [];
      const cards = document.querySelectorAll("[data-asin]");
      cards.forEach(card => {
        const asin = card.getAttribute("data-asin");
        if (!asin || asin === "") return;
        const titleEl = card.querySelector("h2 a, h2 span, .a-link-normal.a-text-normal");
        const priceEl = card.querySelector(".a-price .a-offscreen, .a-price-whole");
        listings.push({
          asin,
          title: titleEl ? (titleEl.innerText || titleEl.getAttribute("title") || "").trim() : "",
          price: priceEl ? parseFloat(priceEl.innerText.replace(/[^0-9.]/g, "")) : 0,
        });
      });
      const countEl = document.querySelector("[data-cel-widget='search_result_count'], .a-size-medium-plus, .a-size-small-plus");
      const total = countEl ? parseInt(countEl.innerText.replace(/[^0-9]/g, "")) : 0;
      chrome.runtime.sendMessage({ action: "scout_data", data: { listings, total_results: total } });
    });
    return;
  }

  // ── Helper ────────────────────────────────────────────────────
  function waitForSelector(selector, callback, maxWait = 12000) {
    const check = () => {
      const el = document.querySelector(selector);
      if (el) return callback();
      if (Date.now() - start > maxWait) return callback();
      setTimeout(check, 400);
    };
    const start = Date.now();
    check();
  }
})();
