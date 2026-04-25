let statsIntervalId = setInterval(updateStats, 1000);

let lastLoggedIdentity = "";

function addLog(message) {
    const log = document.getElementById('log');
    if (!log) return;
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    const now = new Date();
    const ts = now.toTimeString().slice(0, 8);
    entry.textContent = `[${ts}] ${message}`;
    log.prepend(entry);
    if (log.children.length > 50) log.removeChild(log.lastChild);
}

function startCamera() {
    const img = document.getElementById('videoFeed');
    const msg = document.getElementById('noCameraMsg');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    fetch('/start_camera')
        .then(response => {
            if (response.ok) {
                img.src = "/video_feed";
                img.style.display = "block";
                msg.style.display = "none";
                if (startBtn) startBtn.disabled = true;
                if (stopBtn) stopBtn.disabled = false;
                addLog("Camera started.");
            }
        });
}

function stopCamera() {
    const img = document.getElementById('videoFeed');
    const msg = document.getElementById('noCameraMsg');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    img.src = "";
    img.style.display = "none";
    msg.style.display = "flex";
    fetch('/stop_camera')
        .then(() => {
            if (startBtn) startBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;
            const faceList = document.getElementById('faceList');
            if (faceList) faceList.innerHTML = '<div class="no-faces">No faces detected yet</div>';
            lastLoggedIdentity = "";
            addLog("Camera stopped.");
        });
}

function toggleLive(checkbox) {
    const state = checkbox.checked ? "on" : "off";
    fetch(`/toggle_recognition/${state}`)
        .then(() => {
            if (!checkbox.checked) {
                const faceList = document.getElementById('faceList');
                if (faceList) faceList.innerHTML = '<div class="no-faces">No faces detected yet</div>';
                lastLoggedIdentity = "";
            }
            addLog(`Live recognition ${checkbox.checked ? "enabled" : "paused"}.`);
        });
}

document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('liveToggle');
    if (toggle) toggle.addEventListener('change', () => toggleLive(toggle));
});

function updateStats() {
    fetch('/get_stats')
        .then(response => response.json())
        .then(data => {
            const statusDot = document.getElementById('statusDot');
            const statusText = document.getElementById('statusText');
            if (data.status === "ACTIVE") {
                statusDot.classList.add('active');
                statusText.innerText = "System Live";
                statusText.style.color = "#00ffcc";
            } else {
                statusDot.classList.remove('active');
                statusText.innerText = "System Idle";
                statusText.style.color = "#ff3366";
            }

            const statFaces = document.getElementById('statFaces');
            const statKnown = document.getElementById('statKnown');
            const statUnknown = document.getElementById('statUnknown');
            const statTime = document.getElementById('statTime');
            const fpsCounter = document.getElementById('fpsCounter');

            if (statFaces) statFaces.innerText = data.face_found;
            if (statKnown) statKnown.innerText = data.recognized;
            if (statUnknown) statUnknown.innerText = data.unknown;
            if (statTime) statTime.innerText = data.session_time || "00:00";
            if (fpsCounter) fpsCounter.innerText = (data.fps || 0) + " FPS";

            const faceList = document.getElementById('faceList');
            if (faceList) {
                if (data.status === "ACTIVE" && data.current_user && data.current_user !== "") {
                    const isKnown = data.current_user !== "Unknown" && data.current_user !== "Scanning...";
                    faceList.innerHTML = `
                        <div class="face-entry" style="color: ${isKnown ? '#00ffcc' : '#ff3366'}">
                            ${isKnown ? '✓' : '?'} ${data.current_user}
                        </div>`;
                } else {
                    faceList.innerHTML = '<div class="no-faces">No faces detected yet</div>';
                }
            }

            if (data.current_user && data.current_user !== lastLoggedIdentity && data.current_user !== "Scanning...") {
                addLog(`Detected: ${data.current_user}`);
                lastLoggedIdentity = data.current_user;
            }
        })
        .catch(() => {});
}