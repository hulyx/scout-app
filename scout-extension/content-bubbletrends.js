(function() {
  if (!window.location.href.includes("thebubbletrends.com")) return;

  function waitForTable(callback, maxWait = 35000) {
    const start = Date.now();
    function check() {
      const rows = document.querySelectorAll("table tbody tr");
      if (rows.length >= 5) return callback(rows);
      if (Date.now() - start > maxWait) {
        return callback(document.querySelectorAll("table tbody tr"));
      }
      setTimeout(check, 600);
    }
    check();
  }

  waitForTable((rows) => {
    const items = [];
    const seen = new Set();
    rows.forEach((row) => {
      const cells = row.querySelectorAll("td");
      if (cells.length < 3) return;
      const link = cells[1].querySelector("a");
      const keyword = link ? (link.innerText || link.textContent || "").trim() : (cells[1].innerText || "").trim();
      const countText = (cells[2].innerText || cells[2].textContent || "").trim();
      const resultCount = parseInt(countText.replace(/[^0-9]/g, ""), 10) || 0;
      if (keyword && keyword.length >= 3 && !seen.has(keyword.toLowerCase())) {
        seen.add(keyword.toLowerCase());
        items.push({ keyword, result_count: resultCount });
      }
    });
    chrome.runtime.sendMessage({
      action: "scout_data",
      data: { listings: items, total_results: items.length },
    });
  });
})();
