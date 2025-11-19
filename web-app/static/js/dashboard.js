let webcamStream = null;

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("image-input");
  const previewImage = document.getElementById("preview-image");
  const previewLabel = document.getElementById("preview-label");
  const enableWebcamBtn = document.getElementById("enable-webcam-btn");
  const captureBtn = document.getElementById("capture-btn");
  const webcamStatus = document.getElementById("webcam-status");

  input.addEventListener("change", () => {
    if (input.files && input.files[0]) {
      const file = input.files[0];
      const reader = new FileReader();

      reader.onload = (e) => {
        previewImage.src = e.target.result;
        previewImage.style.display = "block";
        previewLabel.style.display = "block";
      };

      reader.readAsDataURL(file);
    }
  });

  enableWebcamBtn.addEventListener("click", () => {
    startWebcam(enableWebcamBtn, captureBtn, webcamStatus);
  });

  captureBtn.addEventListener("click", () => {
    captureFromWebcam(webcamStatus);
  });
});

// Convert file → Base64 string
async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => {
      // Remove the "data:image/jpeg;base64," prefix
      const base64String = reader.result.split(",")[1];
      resolve(base64String);
    };

    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// Upload user image → POST /api/snapshots
async function uploadImage() {
  const input = document.getElementById("image-input");
  const statusEl = document.getElementById("upload-status");
  const snapshotJsonEl = document.getElementById("current-snapshot-json");

  if (!input.files || input.files.length === 0) {
    statusEl.textContent = "Please choose an image.";
    return;
  }

  // Read file → base64 and send to server
  const file = input.files[0];
  statusEl.textContent = "Converting image…";
  const base64 = await fileToBase64(file);
  await sendImageToServer(base64, statusEl, snapshotJsonEl);
}

async function sendImageToServer(base64, statusEl, snapshotJsonEl) {
  statusEl.textContent = "Uploading to server…";
  const resp = await fetch("/api/snapshots", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_data: base64 }),
  });

  if (!resp.ok) {
    statusEl.textContent = "Upload failed.";
    return;
  }

  const data = await resp.json();
  statusEl.textContent = `Snapshot created: ${data.id}`;
  snapshotJsonEl.textContent = JSON.stringify(data, null, 2);
  updateAnalysisSummary({ id: data.id, status: "pending" });

  // Start polling until ML client finishes processing
  pollSnapshotStatus(data.id);
}

// Poll snapshot status → GET /api/snapshots/<id>
async function pollSnapshotStatus(id) {
  const snapshotJsonEl = document.getElementById("current-snapshot-json");

  const intervalId = setInterval(async () => {
    const resp = await fetch(`/api/snapshots/${id}`);
    if (!resp.ok) {
      snapshotJsonEl.textContent = "Error polling snapshot.";
      clearInterval(intervalId);
      return;
    }

    const view = await resp.json();
    snapshotJsonEl.textContent = JSON.stringify(view, null, 2);
    updateAnalysisSummary(view);

    // If done → stop polling and refresh recent table
    if (view.status === "done" || view.status === "error") {
      clearInterval(intervalId);
      loadRecentSnapshots();
    }
  }, 2000);
}

// Load recent snapshots → GET /api/snapshots
async function loadRecentSnapshots() {
  const tableBody = document.querySelector("#snapshot-table tbody");
  tableBody.innerHTML = "";

  const resp = await fetch("/api/snapshots");
  if (!resp.ok) {
    tableBody.innerHTML = "<tr><td colspan='5'>Failed to load snapshots.</td></tr>";
    return;
  }

  const data = await resp.json();

  data.items.forEach((item) => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>${item.id || ""}</td>
      <td>${item.status || (item.processed ? "done" : "pending")}</td>
      <td>${item.mood || ""}</td>
      <td>${item.face_detected ? "Yes" : "No"}</td>
      <td>${item.created_at || ""}</td>
    `;

    tableBody.appendChild(tr);
  });
}

// When page loads
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("upload-btn").addEventListener("click", uploadImage);
  loadRecentSnapshots();
  updateAnalysisSummary();
});

async function startWebcam(enableBtn, captureBtn, statusEl) {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    statusEl.textContent = "Webcam not supported in this browser.";
    return;
  }

  try {
    webcamStream = await navigator.mediaDevices.getUserMedia({ video: true });
    const videoElement = document.getElementById("webcam-video");
    videoElement.srcObject = webcamStream;
    captureBtn.disabled = false;
    enableBtn.disabled = true;
    statusEl.textContent = "Camera ready.";
  } catch (err) {
    statusEl.textContent = "Unable to access webcam.";
    console.error("Webcam error", err);
  }
}

async function captureFromWebcam(statusEl) {
  if (!webcamStream) {
    statusEl.textContent = "Enable the webcam first.";
    return;
  }

  const videoElement = document.getElementById("webcam-video");
  const canvas = document.getElementById("webcam-canvas");
  const snapshotJsonEl = document.getElementById("current-snapshot-json");

  const width = videoElement.videoWidth || 640;
  const height = videoElement.videoHeight || 480;
  canvas.width = width;
  canvas.height = height;

  const ctx = canvas.getContext("2d");
  ctx.drawImage(videoElement, 0, 0, width, height);

  const dataUrl = canvas.toDataURL("image/jpeg", 0.95);
  const base64 = dataUrl.split(",")[1];

  await sendImageToServer(base64, statusEl, snapshotJsonEl);
}

function updateAnalysisSummary(view) {
  const moodTextEl = document.getElementById("analysis-mood-text");
  const snapshotJsonEl = document.getElementById("current-snapshot-json");

  if (!view || Object.keys(view).length === 0) {
    moodTextEl.textContent = "Mood: —";
    snapshotJsonEl.textContent = "No snapshot yet.";
    return;
  }

  const mood = view.mood || (view.status === "pending" ? "Pending" : "Unknown");
  moodTextEl.textContent = `Mood: ${mood}`;
  snapshotJsonEl.textContent = JSON.stringify(view, null, 2);
}
