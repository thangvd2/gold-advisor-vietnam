var priceChartInstance = null;
var gapChartInstance = null;

var PRICE_CONFIG = {
  sjc_bar: { label: 'SJC Bar', borderColor: '#D4AF37', backgroundColor: 'rgba(212,175,55,0.08)' },
  ring_gold: { label: 'Ring Gold', borderColor: '#E07A5F', backgroundColor: 'rgba(224,122,95,0.08)' },
  local_ring_gold: { label: 'Local Ring Gold', borderColor: '#A78BFA', backgroundColor: 'rgba(167,139,250,0.08)', borderDash: [6, 3] },
  xau_usd: { label: 'Intl Gold', borderColor: '#4A90D9', backgroundColor: 'rgba(74,144,217,0.08)' }
};

var GAP_CONFIG = {
  gap_pct: { label: 'Gap %', borderColor: '#D4AF37', backgroundColor: 'rgba(212,175,55,0.08)' },
  ma_7d: { label: '7d MA', borderColor: '#B0B0B0', backgroundColor: 'transparent', borderDash: [5, 5] },
  ma_30d: { label: '30d MA', borderColor: '#909090', backgroundColor: 'transparent', borderDash: [8, 4] }
};

function getChartDefaults(extra) {
  var defaults = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 400 },
    plugins: {
      legend: { display: true, position: 'top', align: 'end', labels: { color: '#E0E0E0', usePointStyle: true, pointStyle: 'line', padding: 16, font: { size: 11, family: 'DM Sans' } } },
      tooltip: {
        backgroundColor: '#1E1E1E',
        borderColor: 'rgba(212,175,55,0.3)',
        borderWidth: 1,
        titleColor: '#F5F5F5',
        bodyColor: '#E0E0E0',
        padding: 12,
        cornerRadius: 8,
        titleFont: { family: 'DM Sans', weight: '600' },
        bodyFont: { family: 'DM Sans' }
      }
    },
    scales: {
      x: {
        type: 'time',
        time: { timezone: 'Asia/Ho_Chi_Minh', tooltipFormat: 'dd/MM/yyyy HH:mm', displayFormats: { minute: 'HH:mm', hour: 'HH:mm', day: 'dd/MM' } },
        grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false },
        ticks: { color: '#B0B0B0', font: { size: 11, family: 'DM Sans' }, maxTicksLimit: 8 }
      },
      y: {
        grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false },
        ticks: { color: '#B0B0B0', font: { size: 11, family: 'DM Sans' } }
      }
    },
    interaction: { intersect: false, mode: 'index' }
  };
  if (extra) {
    for (var key in extra) {
      if (extra.hasOwnProperty(key)) {
        defaults[key] = extra[key];
      }
    }
  }
  return defaults;
}

function formatVND(value) {
  if (value == null) return '—';
  return value.toLocaleString('vi-VN') + ' VND';
}

async function fetchChartData(url) {
  try {
    var resp = await fetch(url);
    if (!resp.ok) return null;
    return await resp.json();
  } catch (e) {
    console.warn('Chart data fetch failed:', url, e);
    return null;
  }
}

function setActiveButton(containerId, activeRange) {
  var container = document.getElementById(containerId);
  if (!container) return;
  container.querySelectorAll('.tf-btn').forEach(function(btn) {
    if (btn.dataset.range === activeRange) {
      btn.classList.remove('text-charcoal-400');
      btn.classList.add('bg-gold-500', 'text-charcoal-900');
    } else {
      btn.classList.remove('bg-gold-500', 'text-charcoal-900');
      btn.classList.add('text-charcoal-400');
    }
  });
}

function toTimePoints(prices) {
  return prices.map(function(p) { return { x: new Date(p.x), y: p.y }; });
}

var RANGE_MS = { '1D': 86400000, '1W': 604800000, '1M': 2592000000, '3M': 7776000000, '1Y': 31536000000 };

function padToRange(points, range) {
  if (!points || !points.length || !RANGE_MS[range]) return points;
  var now = Date.now();
  var rangeStart = now - RANGE_MS[range];
  var padded = [];
  if (points[0].x.getTime() > rangeStart) {
    padded.push({ x: new Date(rangeStart), y: null });
  }
  for (var i = 0; i < points.length; i++) { padded.push(points[i]); }
  if (points[points.length - 1].x.getTime() < now) {
    padded.push({ x: new Date(now), y: null });
  }
  return padded;
}

function setAxisRange(chart, range) {
  if (RANGE_MS[range]) {
    chart.options.scales.x.min = new Date(Date.now() - RANGE_MS[range]);
    chart.options.scales.x.max = new Date();
  }
}

function initPriceChart(canvasId, defaultRange) {
  var canvas = document.getElementById(canvasId);
  if (!canvas) return;

  if (priceChartInstance) {
    priceChartInstance.destroy();
    priceChartInstance = null;
  }

  var defaults = getChartDefaults({
    scales: {
      x: { type: 'time', time: { timezone: 'Asia/Ho_Chi_Minh', tooltipFormat: 'dd/MM/yyyy HH:mm', displayFormats: { minute: 'HH:mm', hour: 'HH:mm', day: 'dd/MM' } }, grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false }, ticks: { color: '#B0B0B0', font: { size: 11, family: 'DM Sans' }, maxTicksLimit: 8 } },
      y: { grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false }, ticks: { color: '#B0B0B0', font: { size: 11, family: 'DM Sans' }, callback: function(value) { return (value / 1000000).toFixed(1) + 'M'; } } }
    },
    plugins: {
      legend: { display: true, position: 'top', align: 'end', labels: { color: '#E0E0E0', usePointStyle: true, pointStyle: 'line', padding: 16, font: { size: 11, family: 'DM Sans' } } },
      tooltip: {
        backgroundColor: '#1E1E1E', borderColor: 'rgba(212,175,55,0.3)', borderWidth: 1,
        titleColor: '#F5F5F5', bodyColor: '#E0E0E0', padding: 12, cornerRadius: 8,
        titleFont: { family: 'DM Sans', weight: '600' }, bodyFont: { family: 'DM Sans' },
        callbacks: { label: function(context) { return context.dataset.label + ': ' + formatVND(context.parsed.y); } }
      }
    },
    interaction: { intersect: false, mode: 'index' }
  });

  priceChartInstance = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: { datasets: [] },
    options: defaults
  });

  loadPriceData(defaultRange);
}

async function loadPriceData(range) {
  var fetches = [
    fetchChartData('/api/prices/history?product_type=sjc_bar&range=' + range),
    fetchChartData('/api/prices/history?product_type=ring_gold&range=' + range),
    fetchChartData('/api/prices/history?product_type=xau_usd&range=' + range),
    fetchChartData('/api/prices/history?product_type=ring_gold&source=local&range=' + range)
  ];
  var results = await Promise.all(fetches);

  if (priceChartInstance) {
    var datasets = [];
    var productTypes = ['sjc_bar', 'ring_gold', 'xau_usd', 'local_ring_gold'];

    for (var i = 0; i < productTypes.length; i++) {
      var data = results[i];
      var config = PRICE_CONFIG[productTypes[i]];
      var points = data && data.prices ? padToRange(toTimePoints(data.prices), range) : [];

      datasets.push({
        label: config.label,
        data: points,
        borderColor: config.borderColor,
        backgroundColor: config.backgroundColor,
        borderWidth: config.borderDash ? 2 : 2,
        borderDash: config.borderDash || [],
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
        fill: false,
        spanGaps: false
      });
    }

    priceChartInstance.data.datasets = datasets;
    setAxisRange(priceChartInstance, range);
    priceChartInstance.update('none');
  }
}

function updatePriceRange(range) {
  setActiveButton('price-timeframe-btns', range);
  loadPriceData(range);
}

function initGapChart(canvasId, defaultRange) {
  var canvas = document.getElementById(canvasId);
  if (!canvas) return;

  if (gapChartInstance) {
    gapChartInstance.destroy();
    gapChartInstance = null;
  }

  var defaults = getChartDefaults({
    scales: {
      x: { type: 'time', time: { timezone: 'Asia/Ho_Chi_Minh', tooltipFormat: 'dd/MM/yyyy HH:mm', displayFormats: { minute: 'HH:mm', hour: 'HH:mm', day: 'dd/MM' } }, grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false }, ticks: { color: '#B0B0B0', font: { size: 11, family: 'DM Sans' }, maxTicksLimit: 8 } },
      y: { title: { display: true, text: 'Gap (%)', color: '#B0B0B0', font: { size: 11, family: 'DM Sans' } }, grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false }, ticks: { color: '#B0B0B0', font: { size: 11, family: 'DM Sans' } } }
    },
    plugins: {
      legend: { display: true, position: 'top', align: 'end', labels: { color: '#E0E0E0', usePointStyle: true, pointStyle: 'line', padding: 16, font: { size: 11, family: 'DM Sans' } } },
      tooltip: {
        backgroundColor: '#1E1E1E', borderColor: 'rgba(212,175,55,0.3)', borderWidth: 1,
        titleColor: '#F5F5F5', bodyColor: '#E0E0E0', padding: 12, cornerRadius: 8,
        titleFont: { family: 'DM Sans', weight: '600' }, bodyFont: { family: 'DM Sans' },
        callbacks: { label: function(context) { if (context.parsed.y == null) return context.dataset.label + ': —'; return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + '%'; } }
      }
    },
    interaction: { intersect: false, mode: 'index' }
  });

  gapChartInstance = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: { datasets: [] },
    options: defaults
  });

  loadGapData(defaultRange);
}

async function loadGapData(range) {
  var data = await fetchChartData('/api/gap/history?range=' + range);

  if (gapChartInstance && data && data.gaps) {
    var gapPoints = data.gaps.map(function(g) { return { x: new Date(g.timestamp), y: g.gap_pct }; });
    var ma7Points = data.gaps.map(function(g) { return { x: new Date(g.timestamp), y: g.ma_7d }; });
    var ma30Points = data.gaps.map(function(g) { return { x: new Date(g.timestamp), y: g.ma_30d }; });

    gapChartInstance.data.datasets = [
      {
        label: GAP_CONFIG.gap_pct.label,
        data: padToRange(gapPoints, range),
        borderColor: GAP_CONFIG.gap_pct.borderColor,
        backgroundColor: GAP_CONFIG.gap_pct.backgroundColor,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
        fill: false,
        spanGaps: false
      },
      {
        label: GAP_CONFIG.ma_7d.label,
        data: padToRange(ma7Points, range),
        borderColor: GAP_CONFIG.ma_7d.borderColor,
        backgroundColor: GAP_CONFIG.ma_7d.backgroundColor,
        borderWidth: 1.5,
        borderDash: GAP_CONFIG.ma_7d.borderDash,
        pointRadius: 0,
        pointHoverRadius: 3,
        tension: 0.3,
        fill: false,
        spanGaps: false
      },
      {
        label: GAP_CONFIG.ma_30d.label,
        data: padToRange(ma30Points, range),
        borderColor: GAP_CONFIG.ma_30d.borderColor,
        backgroundColor: GAP_CONFIG.ma_30d.backgroundColor,
        borderWidth: 1.5,
        borderDash: GAP_CONFIG.ma_30d.borderDash,
        pointRadius: 0,
        pointHoverRadius: 3,
        tension: 0.3,
        fill: false,
        spanGaps: false
      }
    ];
    setAxisRange(gapChartInstance, range);
    gapChartInstance.update('none');
  }
}

function updateGapRange(range) {
  setActiveButton('gap-timeframe-btns', range);
  loadGapData(range);
}
