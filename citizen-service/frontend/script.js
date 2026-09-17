const API_URL = "http://127.0.0.1:5000/api";

const PATTERNS = {
    phone: /^[6-9]\d{9}$/,
    aadhaarRaw: /^[2-9]\d{11}$/,
    name: /^[A-Za-z\s.]{2,50}$/,
    email: /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/,
    pincode: /^[1-9]\d{5}$/,
    ward: /^(WARD-)?\d{1,3}$/i
};

document.addEventListener("DOMContentLoaded", () => {
    setupInputValidation();
});

function setupInputValidation() {
    // Phone
    const phone = document.getElementById("phone");
    phone.addEventListener("input", () => {
        phone.value = phone.value.replace(/\D/g, "").slice(0, 10);
        const hint = document.getElementById("phoneHint");
        if (PATTERNS.phone.test(phone.value)) {
            phone.className = "is-valid";
            hint.className = "hint success";
            hint.innerText = "✓ Valid 10-digit mobile number";
        } else {
            phone.className = "is-invalid";
            hint.className = "hint error";
            hint.innerText = "Must be exactly 10 digits starting with 6, 7, 8, or 9";
        }
    });

    // Aadhaar
    const aadhaar = document.getElementById("aadhaar");
    aadhaar.addEventListener("input", () => {
        let digits = aadhaar.value.replace(/\D/g, "").slice(0, 12);
        let formatted = "";
        for (let i = 0; i < digits.length; i++) {
            if (i > 0 && i % 4 === 0) formatted += " ";
            formatted += digits[i];
        }
        aadhaar.value = formatted;

        const hint = document.getElementById("aadhaarHint");
        if (digits.length === 12 && digits[0] !== "0" && digits[0] !== "1") {
            aadhaar.className = "is-valid";
            hint.className = "hint success";
            hint.innerText = "✓ Valid 12-digit Aadhaar format";
        } else {
            aadhaar.className = "is-invalid";
            hint.className = "hint error";
            hint.innerText = digits[0] === "0" || digits[0] === "1" ? "Aadhaar cannot start with 0 or 1" : `Enter 12 digits (${digits.length}/12)`;
        }
    });

    // Name
    const name = document.getElementById("name");
    name.addEventListener("input", () => {
        const hint = document.getElementById("nameHint");
        if (PATTERNS.name.test(name.value.trim())) {
            name.className = "is-valid";
            hint.className = "hint success";
            hint.innerText = "✓ Valid name";
        } else {
            name.className = "is-invalid";
            hint.className = "hint error";
            hint.innerText = "Letters, dots, and spaces only (2-50 characters)";
        }
    });
}

document.getElementById("citizenForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    const name = document.getElementById("name").value.trim();
    const phone = document.getElementById("phone").value.trim();
    const aadhaar = document.getElementById("aadhaar").value.trim();
    const email = document.getElementById("email").value.trim();
    const ward = document.getElementById("ward").value.trim();
    const pincode = document.getElementById("pincode").value.trim();
    const result = document.getElementById("result");

    try {
        const res = await fetch(`${API_URL}/citizens`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, phone, aadhaar, email, ward, pincode })
        });
        const data = await res.json();

        result.style.display = "block";
        if (res.ok) {
            result.className = "result-box success";
            result.innerHTML = `
                <strong>✓ Registration Successful!</strong><br>
                Citizen ID: <strong>#${data.citizen_id}</strong><br>
                Name: ${data.name} | Ward: ${data.ward}<br>
                Phone: +91 ${data.phone} | Aadhaar: ${data.aadhaar}
            `;
            document.getElementById("citizenForm").reset();
        } else {
            result.className = "result-box error";
            result.innerHTML = `
                <strong>✕ Registration Failed:</strong> ${data.error}<br>
                ${data.field_errors ? Object.values(data.field_errors).map(msg => `• ${msg}`).join("<br>") : ""}
            `;
        }
    } catch (err) {
        result.style.display = "block";
        result.className = "result-box error";
        result.innerHTML = "<strong>✕ Network Error:</strong> API Gateway or Citizen Service is unavailable.";
    }
});

async function findCitizen() {
    const id = document.getElementById("searchId").value.trim();
    const container = document.getElementById("citizenDetails");

    if (!id) {
        container.innerHTML = `<p class="placeholder-text" style="color:var(--rose);">Please enter a Citizen ID.</p>`;
        return;
    }

    try {
        const res = await fetch(`${API_URL}/citizens/${id}`);
        const data = await res.json();

        if (res.ok) {
            container.innerHTML = `
                <div style="color:var(--primary); font-weight:700; margin-bottom:8px;">Citizen Record #${data.citizen_id}</div>
                <strong>Name:</strong> ${data.name}<br>
                <strong>Ward:</strong> ${data.ward}<br>
                <strong>Phone:</strong> +91 ${data.phone}<br>
                <strong>Aadhaar:</strong> ${data.masked_aadhaar || data.aadhaar}<br>
                <strong>Email:</strong> ${data.email || "Not Provided"}<br>
                <strong>PIN Code:</strong> ${data.pincode || "Not Provided"}
            `;
        } else {
            container.innerHTML = `<p class="placeholder-text" style="color:var(--rose);">${data.error || "Citizen not found."}</p>`;
        }
    } catch (err) {
        container.innerHTML = `<p class="placeholder-text" style="color:var(--rose);">Citizen Service is unavailable.</p>`;
    }
}