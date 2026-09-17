const API_URL = "http://127.0.0.1:5000/api";

const DEPT_CODE_REGEX = /^DEPT-[A-Z]{3}-\d{3}$/;
const CONTACT_REGEX = /^(1800\d{6,7}|[6-9]\d{9})$/;

document.addEventListener("DOMContentLoaded", () => {
    setupDeptValidation();
    loadDepartments();
});

function setupDeptValidation() {
    const codeInput = document.getElementById("code");
    codeInput.addEventListener("input", () => {
        codeInput.value = codeInput.value.toUpperCase();
        const hint = document.getElementById("codeHint");
        if (DEPT_CODE_REGEX.test(codeInput.value)) {
            codeInput.className = "is-valid";
            hint.className = "hint success";
            hint.innerText = "✓ Valid Department ID standard pattern";
        } else {
            codeInput.className = "is-invalid";
            hint.className = "hint error";
            hint.innerText = "Must strictly match DEPT-[SECTOR]-[NUM] (e.g. DEPT-WAT-101)";
        }
    });

    const contactInput = document.getElementById("contact");
    contactInput.addEventListener("input", () => {
        contactInput.value = contactInput.value.replace(/\D/g, "").slice(0, 11);
        const hint = document.getElementById("contactHint");
        if (CONTACT_REGEX.test(contactInput.value)) {
            contactInput.className = "is-valid";
            hint.className = "hint success";
            hint.innerText = "✓ Valid contact number";
        } else {
            contactInput.className = "is-invalid";
            hint.className = "hint error";
            hint.innerText = "10-digit mobile or municipal 1800 number";
        }
    });
}

async function handleDeptSubmit(e) {
    e.preventDefault();
    const code = document.getElementById("code").value.trim().toUpperCase();
    const name = document.getElementById("name").value.trim();
    const contact = document.getElementById("contact").value.trim();
    const email = document.getElementById("email").value.trim();
    const description = document.getElementById("description").value.trim();
    const result = document.getElementById("result");

    try {
        const res = await fetch(`${API_URL}/departments`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code, name, contact, email, description })
        });
        const data = await res.json();

        result.style.display = "block";
        if (res.ok) {
            result.className = "result-box success";
            result.innerHTML = `
                <strong>✓ Department Created!</strong><br>
                Code: <strong>${data.department.code}</strong> | ID: #${data.department.id}<br>
                Name: ${data.department.name}
            `;
            document.getElementById("deptForm").reset();
            loadDepartments();
        } else {
            result.className = "result-box error";
            result.innerHTML = `<strong>✕ Creation Failed:</strong> ${data.error}`;
        }
    } catch (err) {
        result.style.display = "block";
        result.className = "result-box error";
        result.innerHTML = "<strong>✕ Network Error:</strong> API Gateway or Department Service unavailable.";
    }
}

async function loadDepartments() {
    const list = document.getElementById("departmentsList");
    try {
        const res = await fetch(`${API_URL}/departments`);
        const data = await res.json();

        if (res.ok && data.length > 0) {
            list.innerHTML = data.map(d => `
                <div class="mini-dept-item" onclick="selectDept('${d.code || d.id}')">
                    <div>
                        <code>${d.code}</code>
                        <div style="color:#fff; font-size:12px; font-weight:600; margin-top:2px;">${d.name}</div>
                    </div>
                    <span style="color:var(--text-muted); font-size:11px;">📞 ${d.contact}</span>
                </div>
            `).join("");
        } else {
            list.innerHTML = `<div class="placeholder-text">No departments found.</div>`;
        }
    } catch (err) {
        list.innerHTML = `<div class="placeholder-text" style="color:var(--rose);">Department service unavailable.</div>`;
    }
}

function selectDept(idOrCode) {
    document.getElementById("deptLookupId").value = idOrCode;
    loadDepartmentComplaints();
}

async function loadDepartmentComplaints() {
    const id = document.getElementById("deptLookupId").value.trim();
    const details = document.getElementById("deptDetails");
    if (!id) {
        details.innerHTML = `<p class="placeholder-text" style="color:var(--rose);">Enter a Department ID or Code.</p>`;
        return;
    }

    try {
        const res = await fetch(`${API_URL}/departments/${id}/complaints`);
        const data = await res.json();

        if (res.ok) {
            const comps = data.complaints || [];
            details.innerHTML = `
                <strong style="color:var(--primary);">${data.department_code || id} - ${data.department}</strong><br>
                <span>Total Assigned Complaints: <strong>${data.complaint_count}</strong></span>
                <hr style="border-color:var(--border); margin:8px 0;">
                ${comps.length === 0 ? `<p class="placeholder-text">No complaints active for this department.</p>` : comps.map(c => `
                    <div style="margin-bottom:6px; font-size:11px;">
                        <strong>${c.complaint_code || "#" + c.id}</strong> | ${c.location} &bull; 
                        <span style="color:${c.status === 'OPEN' ? 'var(--rose)' : 'var(--emerald)'}">${c.status}</span><br>
                        <em>"${c.description}"</em>
                    </div>
                `).join("")}
            `;
        } else {
            details.innerHTML = `<p class="placeholder-text" style="color:var(--rose);">${data.error || "Department not found."}</p>`;
        }
    } catch (err) {
        details.innerHTML = `<p class="placeholder-text" style="color:var(--rose);">Department Service is unavailable.</p>`;
    }
}

async function loadDepartmentCitizens() {
    const id = document.getElementById("deptLookupId").value.trim();
    const details = document.getElementById("deptDetails");
    if (!id) {
        details.innerHTML = `<p class="placeholder-text" style="color:var(--rose);">Enter a Department ID or Code.</p>`;
        return;
    }

    try {
        const res = await fetch(`${API_URL}/departments/${id}/citizens`);
        const data = await res.json();

        if (res.ok) {
            const citizens = data.citizens || [];
            details.innerHTML = `
                <strong style="color:var(--primary);">${data.department_code || id} - ${data.department}</strong><br>
                <span>Impacted Citizens: <strong>${data.citizen_count}</strong></span>
                <hr style="border-color:var(--border); margin:8px 0;">
                ${citizens.length === 0 ? `<p class="placeholder-text">No citizen grievances on file.</p>` : citizens.map(c => `
                    <div style="margin-bottom:6px; font-size:11px;">
                        <strong>#${c.citizen_id} - ${c.name}</strong> &bull; Ward: ${c.ward} &bull; 📞 +91 ${c.phone}
                    </div>
                `).join("")}
            `;
        } else {
            details.innerHTML = `<p class="placeholder-text" style="color:var(--rose);">${data.error || "Department not found."}</p>`;
        }
    } catch (err) {
        details.innerHTML = `<p class="placeholder-text" style="color:var(--rose);">Department Service is unavailable.</p>`;
    }
}