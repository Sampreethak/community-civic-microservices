const API_URL = "http://127.0.0.1:5000/api";

async function handleSubmit(e) {
    e.preventDefault();

    const citizenId = document.getElementById("citizenId").value.trim();
    const deptInput = document.getElementById("departmentId").value.trim();
    const priority = document.querySelector('input[name="priority"]:checked').value;
    const location = document.getElementById("location").value.trim();
    const description = document.getElementById("description").value.trim();
    const result = document.getElementById("result");

    if (description.length < 10) {
        alert("Description must be at least 10 characters long.");
        return;
    }

    const payload = {
        citizen_id: Number(citizenId),
        description: description,
        location: location,
        priority: priority
    };

    if (deptInput.toUpperCase().startsWith("DEPT-")) {
        payload.department_code = deptInput.toUpperCase();
    } else {
        payload.department_id = deptInput;
    }

    try {
        const res = await fetch(`${API_URL}/complaints`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        result.style.display = "block";
        if (res.ok) {
            result.className = "result-box success";
            result.innerHTML = `
                <strong>✓ Grievance Logged Successfully!</strong><br>
                Tracking Code: <strong>${data.complaint_code}</strong> (ID #${data.complaint_id})<br>
                Citizen: ${data.citizen_name} &bull; Priority: ${data.priority}<br>
                Assigned: ${data.department_code || "Dept #" + data.department_id}
            `;
            document.getElementById("complaintForm").reset();
        } else {
            result.className = "result-box error";
            result.innerHTML = `<strong>✕ Error:</strong> ${data.error}`;
        }
    } catch (err) {
        result.style.display = "block";
        result.className = "result-box error";
        result.innerHTML = "<strong>✕ Network Error:</strong> API Gateway or Complaint Service unavailable.";
    }
}

async function findComplaint() {
    const query = document.getElementById("searchComplaintId").value.trim();
    const details = document.getElementById("complaintDetails");

    if (!query) {
        details.innerHTML = `<p class="placeholder-text" style="color:var(--rose);">Please enter a Complaint ID or Tracking Code.</p>`;
        return;
    }

    try {
        const res = await fetch(`${API_URL}/complaints/${query}`);
        const data = await res.json();

        if (res.ok) {
            details.innerHTML = `
                <div style="font-family:var(--font-mono); font-size:14px; font-weight:700; color:var(--primary); margin-bottom:8px;">
                    ${data.complaint_code || "#" + data.complaint_id}
                </div>
                <strong>Citizen:</strong> ${data.citizen_name} (ID #${data.citizen_id})<br>
                <strong>Assigned To:</strong> ${data.department_code || "Dept #" + data.department_id}<br>
                <strong>Location:</strong> ${data.location}<br>
                <strong>Priority:</strong> ${data.priority || 'MEDIUM'} &bull; 
                <strong>Status:</strong> <span style="color:${data.status === 'RESOLVED' ? 'var(--emerald)' : 'var(--rose)'}; font-weight:700;">${data.status}</span><br>
                <strong>Description:</strong> "${data.description}"
            `;
        } else {
            details.innerHTML = `<p class="placeholder-text" style="color:var(--rose);">${data.error || "Complaint not found."}</p>`;
        }
    } catch (err) {
        details.innerHTML = `<p class="placeholder-text" style="color:var(--rose);">Complaint Service is unavailable.</p>`;
    }
}