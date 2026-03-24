function switchMode(mode) {
  var signalCard = document.getElementById('signal-card');
  if (signalCard) {
    htmx.ajax('GET', '/dashboard/partials/signal?mode=' + mode, { target: '#signal-card', swap: 'innerHTML' });
  }
}

document.addEventListener('htmx:responseError', function(evt) {
  console.warn('HTMX request failed:', evt.detail);
});

document.addEventListener('htmx:afterSwap', function(evt) {
  if (evt.detail.target.id === 'signal-card' && typeof initChartsAfterSwap === 'undefined') {
    var range = document.querySelector('.mode-btn.bg-gold-500');
    if (range) {
      var modeText = range.textContent.trim().toLowerCase();
    }
  }
});
