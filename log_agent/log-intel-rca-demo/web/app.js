const API_BASE = (function(){
  const host = window.location.hostname || 'localhost';
  return `http://${host}:8000`;
})();

document.getElementById("searchBtn").onclick = async () => {
  const text = document.getElementById("searchText").value;
  const service = document.getElementById("searchService").value;
  const res = await fetch(`${API_BASE}/search/logs`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ text, service })
  });
  const data = await res.json();
  document.getElementById("logsOutput").textContent = JSON.stringify(data, null, 2);
};

document.getElementById("rcaBtn").onclick = async () => {
  const question = document.getElementById("rcaQuestion").value;
  const res = await fetch(`${API_BASE}/search/rca`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ question })
  });
  const data = await res.json();
  document.getElementById("rcaOutput").textContent = JSON.stringify(data, null, 2);
};
