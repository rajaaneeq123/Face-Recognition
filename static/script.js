function startCamera() {
    const img = document.getElementById('videoFeed');
    const msg = document.getElementById('noCameraMsg');

    const startBtn = document.querySelector('button[onclick="startCamera()"]');
    const stopBtn = document.querySelector('button[onclick="stopCamera()"]');

    fetch('/start_camera')
        .then(response => {
            if (response.ok) {
                img.src = "/video_feed";
                img.style.display = "block";
                msg.style.display = "none";

                // TOGGLE BUTTONS: Disable Start, Enable Stop
                if(startBtn) startBtn.disabled = true;
                if(stopBtn) stopBtn.disabled = false;

                console.log("Camera started and UI updated.");
            }
        });
}

function stopCamera() {
    const img = document.getElementById('videoFeed');
    const msg = document.getElementById('noCameraMsg');
    const startBtn = document.querySelector('button[onclick="startCamera()"]');
    const stopBtn = document.querySelector('button[onclick="stopCamera()"]');

    img.src = "";
    img.style.display = "none";
    msg.style.display = "flex";

    fetch('/stop_camera')
        .then(() => {
            // TOGGLE BUTTONS: Enable Start, Disable Stop
            if(startBtn) startBtn.disabled = false;
            if(stopBtn) stopBtn.disabled = true;

            console.log("Camera stopped and UI reset.");
        });
}

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

            const facesFound = document.getElementById('statFaces');
            if (facesFound) facesFound.innerText = data.face_found;

            const statKnown = document.getElementById('statKnown');
            if (statKnown) {
                statKnown.innerText = (data.current_user !== "Unknown" && data.current_user !== "Scanning...") ? "1" : "0";
            }
        })
        .catch(error => console.error('Error:', error));
}
setInterval(updateStats, 1000);