
(function(){
  function sendEvent(eventType, productName){
    try {
      fetch("http://localhost:5055/track", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          event_type: eventType,
          product_name: productName || document.body.getAttribute("data-product") || "",
          source: new URLSearchParams(window.location.search).get("src") || document.referrer || "direct",
          page_url: window.location.href,
          referrer: document.referrer
        })
      });
    } catch(e) {}
  }
  window.LCATrack = sendEvent;
  document.addEventListener("DOMContentLoaded", function(){
    sendEvent("page_view");
    document.querySelectorAll("a[href*='amazon.']").forEach(function(a){
      a.addEventListener("click", function(){
        sendEvent("amazon_click", a.getAttribute("data-product") || "");
      });
    });
  });
})();
