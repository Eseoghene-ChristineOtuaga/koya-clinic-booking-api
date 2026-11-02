const status = document.querySelector("#status");
fetch("/health")
  .then((response) => {
    if (!response.ok) throw new Error("Server not ready");
    return response.json();
  })
  .then((data) => {
    status.textContent = data.status === "ok"
      ? "API online. Database setup is next."
      : "API returned an unexpected status.";
  })
  .catch(() => {
    status.textContent = "Could not reach the API. Check the deployment.";
  });
