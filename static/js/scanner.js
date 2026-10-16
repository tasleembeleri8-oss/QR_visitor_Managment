let currentMode = "checkin";
let isProcessing = false;

const resultBox = document.getElementById("scan-result");
const modeCheckin = document.getElementById("mode-checkin");
const modeCheckout = document.getElementById("mode-checkout");

modeCheckin.addEventListener("click", () => setMode("checkin"));
modeCheckout.addEventListener("click", () => setMode("checkout"));

function setMode(mode) {
    currentMode = mode;
    modeCheckin.classList.toggle("active", mode === "checkin");
    modeCheckout.classList.toggle("active", mode === "checkout");
}

function showResult(ok, message) {
    resultBox.textContent = message;
    resultBox.className = ok ? "ok" : "err";
    // Auto-clear after a few seconds so the scanner is ready for the next person
    setTimeout(() => {
        resultBox.className = "";
    }, 3500);
}

async function handleScannedToken(token) {
    if (isProcessing) return;
    isProcessing = true;

    const endpoint = currentMode === "checkin" ? "/api/checkin" : "/api/checkout";

    try {
        const res = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token }),
        });
        const data = await res.json();
        showResult(data.ok, data.message);
    } catch (err) {
        showResult(false, "Network error — could not reach server.");
    }

    // Small cooldown so the same badge isn't scanned twice in a row
    setTimeout(() => { isProcessing = false; }, 2000);
}

// html5-qrcode works for both webcam (desktop) and phone camera (mobile) —
// it auto-selects the environment-facing camera on phones.
const qrScanner = new Html5Qrcode("reader");

Html5Qrcode.getCameras().then(cameras => {
    if (!cameras || cameras.length === 0) {
        showResult(false, "No camera found on this device.");
        return;
    }
    // Prefer a back/environment camera if labeled as such (typical on phones)
    const backCamera = cameras.find(c => /back|environment/i.test(c.label)) || cameras[0];

    qrScanner.start(
        backCamera.id,
        { fps: 10, qrbox: { width: 240, height: 240 } },
        (decodedText) => handleScannedToken(decodedText.trim()),
        () => { /* ignore per-frame scan failures */ }
    ).catch(() => {
        showResult(false, "Could not start camera. Check browser permissions.");
    });
}).catch(() => {
    showResult(false, "Camera access denied or unavailable.");
});
