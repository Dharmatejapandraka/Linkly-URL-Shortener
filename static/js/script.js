
const form = document.getElementById("shortenForm");
const urlInput = document.getElementById("urlInput");
const shortenBtn = document.getElementById("shortenBtn");
const buttonText = document.getElementById("buttonText");
const message = document.getElementById("message");
const result = document.getElementById("result");

const shortUrl = document.getElementById("shortUrl");
const copyBtn = document.getElementById("copyBtn");

const qrImage = document.getElementById("qrImage");
const qrDownload = document.getElementById("qrDownload");


// Get Django CSRF cookie
function getCookie(name) {
    const cookies = document.cookie.split(";");

    for (const cookie of cookies) {
        const [key, ...value] = cookie.trim().split("=");

        if (key === name) {
            return decodeURIComponent(value.join("="));
        }
    }

    return null;
}


// Display messages
function showMessage(text, type = "error") {
    message.textContent = text;
    message.style.color =
        type === "success" ? "#72e5a1" : "#ff8585";
}


// Shorten URL
form.addEventListener("submit", async (event) => {
    event.preventDefault();

    message.textContent = "";
    result.classList.add("hidden");

    qrImage.classList.add("hidden");
    qrDownload.classList.add("hidden");

    shortenBtn.disabled = true;
    buttonText.textContent = "Creating your link...";

    const formData = new FormData(form);

    try {
        const response = await fetch("/api/shorten/", {
            method: "POST",
            headers: {
                "X-CSRFToken": getCookie("csrftoken")
            },
            body: formData
        });

        const data = await response.json();

        // Require login if visitor is not authenticated
        if (response.status === 401 && data.login_required) {
            showMessage(
                "Please login or register before shortening a URL."
            );

            setTimeout(() => {
                window.location.href = data.login_url || "/login/";
            }, 1200);

            return;
        }

        // Handle other errors
        if (!response.ok) {
            throw new Error(
                data.error || "Unable to shorten URL."
            );
        }

        // Display shortened URL
        shortUrl.href = data.short_url;
        shortUrl.textContent = data.short_url;

        // Generate QR code URL
        const qrUrl =
            `/qr/${encodeURIComponent(data.short_code)}/`;

        // Display QR code
        qrImage.src = qrUrl;
        qrImage.alt = `QR code for ${data.short_url}`;
        qrImage.classList.remove("hidden");

        // Configure QR download
        qrDownload.href = qrUrl;
        qrDownload.download = `${data.short_code}.png`;
        qrDownload.classList.remove("hidden");

        // Display result
        result.classList.remove("hidden");

        showMessage("Your short link is ready!", "success");

    } catch (error) {
        showMessage(error.message);

    } finally {
        shortenBtn.disabled = false;
        buttonText.textContent = "Shorten URL";
    }
});


// Copy shortened URL
copyBtn.addEventListener("click", async () => {
    if (!shortUrl.href || shortUrl.href === "#") {
        showMessage("Generate a short link first.");
        return;
    }

    try {
        await navigator.clipboard.writeText(shortUrl.href);

        copyBtn.textContent = "Copied! ✓";

        setTimeout(() => {
            copyBtn.textContent = "Copy";
        }, 2000);

    } catch (error) {
        showMessage(
            "Unable to copy. Please copy the URL manually."
        );
    }
});


// Handle QR image loading errors
qrImage.addEventListener("error", () => {
    qrImage.classList.add("hidden");
    qrDownload.classList.add("hidden");

    showMessage(
        "Short link created, but QR code generation failed."
    );
});
