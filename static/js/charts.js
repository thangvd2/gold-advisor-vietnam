var priceChartInstance = null;
var gapChartInstance = null;

var PRICE_CONFIG = {
  sjc_bar: { label: 'SJC Bar', borderColor: '#D4AF37', backgroundColor: 'rgba(212,175,55,0.08)' },
  ring_gold: { label: 'Ring Gold', borderColor: '#F5D76E', backgroundColor: 'rgba(245,215,110,0.08)' },
  xau_usd: { label: 'Intl Gold', borderColor: '#4A90D9', backgroundColor: 'rgba(74,144,217,0.08)' }
};

var GAP_CONFIG = {
  gap_pct: { label: 'Gap %', borderColor: '#D4AF37', backgroundColor: 'rgba(212,175,55,0.08)' },
  ma_7d: { label: '7d MA', borderColor: '#888888', backgroundColor: 'transparent', borderDash: [5, 5] },
  ma_30d: { label: '30d MA', borderColor: '#666666', backgroundColor: 'transparent', borderDash: [8, 4] }
};

function getChartDefaults() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 400 },
    plugins: {
      legend: { display: false },
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
        grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false },
        ticks: { color: '#808080', font: { size: 11, family: 'DM Sans' }, maxTicksLimit: 8 }
      },
      y: {
        grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false },
        ticks: { color: '#808080', font: { size: 11, family: 'DM Sans' } }
      }
    },
    interaction: { intersect: false, mode: 'index' }
  };
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

function initPriceChart(canvasId, dataUrl, defaultRange) {
  var canvas = document.getElementById(canvasId);
  if (!canvas) return;

  if (priceChartInstance) {
    priceChartInstance.destroy();
    priceChartInstance = null;
  }

  var ctx = canvas.getContext('2d');
  var defaults = getChartDefaults();
  defaults.scales.y.ticks.callback = function(value) {
    return (value / 1000000).toFixed(1) + 'M';
  };
  defaults.plugins.tooltip.callbacks = {
    label: function(context) {
      return context.dataset.label + ': ' + formatVND(context.parsed.y);
    }
  };

  priceChartInstance = new Chart(ctx, {
    type: 'line',
    data: { labels: [], datasets: [] },
    options: defaults
  });

  loadPriceData(dataUrl, defaultRange);
}

async function loadPriceData(baseUrl, range) {
  var promises = ['sjc_bar', 'ring_gold', 'xau_usd'].map(function(pt) {
    return fetchChartData(baseUrl + '?product_type=' + pt + '&range=' + range);
  });
  var results = await Promise.all(promises);

  if (priceChartInstance) {
    var allLabels = [];
    var datasets = [];
    var productTypes = ['sjc_bar', 'ring_gold', 'xau_usd'];

    for (var i = 0; i < productTypes.length; i++) {
      var data = results[i];
      var config = PRICE_CONFIG[productTypes[i]];
      var points = [];

      if (data && data.prices) {
        for (var j = 0; j < data.prices.length; j++) {
          var label = new Date(data.prices[j].x).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
          if (allLabels.indexOf(label) === -1) {
            allLabels.push(label);
          }
          points.push(data.prices[j].y);
        }
      }

      datasets.push({
        label: config.label,
        data: points,
        borderColor: config.borderColor,
        backgroundColor: config.backgroundColor,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
        fill: false
      });
    }

    priceChartInstance.data.labels = allLabels;
    priceChartInstance.data.datasets = datasets;
    priceChartInstance.update('none');
  }
}

function updatePriceRange(range) {
  setActiveButton('price-timeframe-btns', range);
  loadPriceData('/api/prices/history', range);
}

function initGapChart(canvasId, dataUrl, defaultRange) {
  var canvas = document.getElementById(canvasId);
  if (!canvas) return;

  if (gapChartInstance) {
    gapChartInstance.destroy();
    gapChartInstance = null;
  }

  var ctx = canvas.getContext('2d');
  var defaults = getChartDefaults();
  defaults.scales.y.title = {
    display: true,
    text: 'Gap (%)',
    color: '#808080',
    font: { size: 11, family: 'DM Sans' }
  };
  defaults.plugins.tooltip.callbacks = {
    label: function(context) {
      if (context.parsed.y == null) return context.dataset.label + ': —';
      return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + '%';
    }
  };

  gapChartInstance = new Chart(ctx, {
    type: 'line',
    data: { labels: [], datasets: [] },
    options: defaults
  });

  loadGapData(dataUrl, defaultRange);
}

async function loadGapData(baseUrl, range) {
  var data = await fetchChartData(baseUrl + '?range=' + range);

  if (gapChartInstance && data && data.gaps) {
    var labels = [];
    var gapPoints = [];
    var ma7Points = [];
    var ma30Points = [];

    for (var i = 0; i < data.gaps.length; i++) {
      var g = data.gaps[i];
      labels.push(new Date(g.timestamp).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' }));
      gapPoints.push(g.gap_pct);
      ma7Points.push(g.ma_7d);
      ma30Points.push(g.ma_30d);
    }

    gapChartInstance.data.labels = labels;
    gapChartInstance.data.datasets = [
      {
        label: GAP_CONFIG.gap_pct.label,
        data: gapPoints,
        borderColor: GAP_CONFIG.gap_pct.borderColor,
        backgroundColor: GAP_CONFIG.gap_pct.backgroundColor,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
        fill: false
      },
      {
        label: GAP_CONFIG.ma_7d.label,
        data: ma7Points,
        borderColor: GAP_CONFIG.ma_7d.borderColor,
        backgroundColor: GAP_CONFIG.ma_7d.backgroundColor,
        borderWidth: 1.5,
        borderDash: GAP_CONFIG.ma_7d.borderDash,
        pointRadius: 0,
        pointHoverRadius: 3,
        tension: 0.3,
        fill: false
      },
      {
        label: GAP_CONFIG.ma_30d.label,
        data: ma30Points,
        borderColor: GAP_CONFIG.ma_30d.borderColor,
        backgroundColor: GAP_CONFIG.ma_30d.backgroundColor,
        borderWidth: 1.5,
        borderDash: GAP_CONFIG.ma_30d.borderDash,
        pointRadius: 0,
        pointHoverRadius: 3,
        tension: 0.3,
        fill: false
      }
    ];
    gapChartInstance.update('none');
  }
}

function updateGapRange(range) {
  setActiveButton('gap-timeframe-btns', range);
  loadGapData('/api/gap/history', range);
}
