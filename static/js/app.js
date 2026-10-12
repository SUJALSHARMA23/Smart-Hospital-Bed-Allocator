document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-toggle-password]").forEach(button => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.togglePassword);
      if (!input) return;
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.textContent = show ? "Hide" : "Show";
    });
  });

  document.querySelectorAll("form[data-confirm]").forEach(form => {
    form.addEventListener("submit", event => {
      if (!window.confirm(form.dataset.confirm || "Are you sure?")) event.preventDefault();
    });
  });

  const canvas = document.getElementById("occupancyChart");
  if (canvas && window.occupancyData && window.Chart) {
    const data = window.occupancyData;
    new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: ["Available", "Occupied", "Unavailable"],
        datasets: [{
          data: [data.available, data.occupied, data.other],
          backgroundColor: ["#20b486", "#f3a64a", "#dce3eb"],
          borderWidth: 0,
          hoverOffset: 5
        }]
      },
      options: {
        cutout: "76%",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: true } }
      }
    });
  }
});
