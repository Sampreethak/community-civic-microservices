/**
 * SmartCivic 360 - Production Portal JavaScript
 * Strict Pattern Matching, Microservices Orchestration & Reactive State
 */

const API_BASE = "http://127.0.0.1:5000/api";

// ---------------------------------------------------------
// REGEX PATTERN SPECIFICATIONS
// ---------------------------------------------------------
const PATTERNS = {
    citizenCode: /^CIT-[A-Z0-9]{3,4}-[A-Z0-9]{5}$/,
    phone: /^[6-9]\d{9}$/,
    aadhaarRaw: /^[2-9]\d{11}$/,
    aadhaarFormatted: /^[2-9]\d{3}\s\d{4}\s\d{4}$/,
    name: /^[A-Za-z\s.]{2,50}$/,
    email: /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/,
    pincode: /^[1-9]\d{5}$/,
    ward: /^(WARD-)?\d{1,3}$/i,
    deptCode: /^DEPT-[A-Z]{3}-\d{3}$/,
    deptContact: /^(1800\d{6,7}|[6-9]\d{9})$/,
    complaintCode: /^CMP-\d{4}-[A-Z0-9]{5}$/
};

const SECTORS = {
    "WAT": "Water Supply & Sewerage Board",
    "ELE": "Electricity & Power Distribution",
    "ROA": "Roads, Bridges & Civil Infrastructure",
    "SAN": "Solid Waste & Public Sanitation",
    "HEA": "Public Health & Clinics",
    "REV": "Revenue, Licensing & Property Assessment",
    "TRA": "Traffic, Transit & Urban Mobility",
    "ENV": "Parks, Lakes & Environmental Protection",
    "URB": "Urban Planning & Building Licensing",
    "DIS": "Disaster Response & Fire Safety"
};

// Global App State
let appState = {
    citizens: [],
    departments: [],
    complaints: [],
    instances: [],
    currentComplaint: null,
    activeTab: "overview"
};

// ---------------------------------------------------------
// INITIALIZATION
// ---------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
    initClock();
    setupPatternListeners();
    initTabRouting();
    fetchAllData();
    setInterval(pollTelemetry, 4000);
});

function initClock() {
    function updateClock() {
        const now = new Date();
        const str = now.toLocaleTimeString("en-IN", { hour12: false }) + " IST";
        const el = document.getElementById("clockDisplay");
        if (el) el.innerText = str;
    }
    updateClock();
    setInterval(updateClock, 1000);
}

function initTabRouting() {
    const hash = window.location.hash.replace("#", "") || "overview";
    switchTab(hash);
}

function switchTab(tabId) {
    appState.activeTab = tabId;
    window.location.hash = tabId;

    // Toggle nav buttons
    document.querySelectorAll(".nav-btn").forEach(btn => btn.classList.remove("active"));
    const activeBtn = document.getElementById(`tabBtn${tabId.charAt(0).toUpperCase() + tabId.slice(1)}`);
    if (activeBtn) activeBtn.classList.add("active");

    // Toggle views
    document.querySelectorAll(".tab-view").forEach(v => v.classList.remove("active"));
    const activeView = document.getElementById(`view${tabId.charAt(0).toUpperCase() + tabId.slice(1)}`);
    if (activeView) activeView.classList.add("active");

    // Refresh tab-specific data
    if (tabId === "citizens") loadCitizens();
    if (tabId === "departments") loadDepartments();
    if (tabId === "complaints") { loadComplaints(); populateDeptDropdown(); }
    if (tabId === "telemetry") loadTelemetry();
}

// ---------------------------------------------------------
// REAL-TIME PATTERN VALIDATION LISTENERS
// ---------------------------------------------------------

function setupPatternListeners() {
    // 0. Citizen Code Listener (CIT-[WARD]-[TOKEN])
    const citizenCodeInput = document.getElementById("citizenCodeInput");
    if (citizenCodeInput) {
        citizenCodeInput.addEventListener("input", () => {
            let val = citizenCodeInput.value.toUpperCase();
            citizenCodeInput.value = val;
            const badge = document.getElementById("citizenCodeBadge");
            const feedback = document.getElementById("citizenCodeFeedback");
            if (!val) {
                setFieldNeutral(citizenCodeInput, feedback, badge, "^CIT-[A-Z0-9]{3,4}-[A-Z0-9]{5}$");
            } else if (PATTERNS.citizenCode.test(val)) {
                setFieldValid(citizenCodeInput, feedback, badge, "✓ Valid Citizen ID format (CIT-[WARD]-[TOKEN])");
            } else {
                setFieldInvalid(citizenCodeInput, feedback, badge, "Must match CIT-[WARD]-[TOKEN] (e.g. CIT-W12-89412 or CIT-2026-X89F2)");
            }
        });
    }

    // 1. Citizen Name Listener
    const nameInput = document.getElementById("citizenName");
    if (nameInput) {
        nameInput.addEventListener("input", () => {
            const val = nameInput.value.trim();
            const badge = document.getElementById("nameBadge");
            const feedback = document.getElementById("citizenNameFeedback");
            if (!val) {
                setFieldNeutral(nameInput, feedback, badge, "Letters only (2-50 chars)");
            } else if (PATTERNS.name.test(val)) {
                setFieldValid(nameInput, feedback, badge, "✓ Valid citizen name format");
            } else {
                setFieldInvalid(nameInput, feedback, badge, "Only letters, dots, and spaces allowed (2-50 characters)");
            }
        });
    }

    // 2. Citizen Phone Listener (10 Digits strictly starting with 6-9)
    const phoneInput = document.getElementById("citizenPhone");
    const phoneCounter = document.getElementById("phoneCounter");
    if (phoneInput) {
        phoneInput.addEventListener("input", () => {
            // Strip non-digits
            phoneInput.value = phoneInput.value.replace(/\D/g, "").slice(0, 10);
            const val = phoneInput.value;
            const badge = document.getElementById("phoneBadge");
            const feedback = document.getElementById("citizenPhoneFeedback");

            phoneCounter.innerText = `${val.length}/10`;
            phoneCounter.classList.toggle("full", val.length === 10);

            if (!val) {
                setFieldNeutral(phoneInput, feedback, badge, "Pattern: ^[6-9]\\d{9}$");
            } else if (PATTERNS.phone.test(val)) {
                setFieldValid(phoneInput, feedback, badge, "✓ Valid 10-digit Indian mobile number");
            } else {
                let msg = "Must be exactly 10 digits";
                if (val.length > 0 && !["6", "7", "8", "9"].includes(val[0])) {
                    msg = "Indian mobile numbers must start with 6, 7, 8, or 9";
                } else if (val.length < 10) {
                    msg = `Enter ${10 - val.length} more digit(s)`;
                }
                setFieldInvalid(phoneInput, feedback, badge, msg);
            }
        });
    }

    // 3. Citizen Aadhaar Listener (12 Digits with auto-formatting XXXX XXXX XXXX)
    const aadhaarInput = document.getElementById("citizenAadhaar");
    const aadhaarCounter = document.getElementById("aadhaarCounter");
    if (aadhaarInput) {
        aadhaarInput.addEventListener("input", (e) => {
            let digits = aadhaarInput.value.replace(/\D/g, "").slice(0, 12);
            // Format as XXXX XXXX XXXX
            let formatted = "";
            for (let i = 0; i < digits.length; i++) {
                if (i > 0 && i % 4 === 0) formatted += " ";
                formatted += digits[i];
            }
            aadhaarInput.value = formatted;

            const badge = document.getElementById("aadhaarBadge");
            const feedback = document.getElementById("citizenAadhaarFeedback");
            aadhaarCounter.innerText = `${digits.length}/12`;
            aadhaarCounter.classList.toggle("full", digits.length === 12);

            if (!digits) {
                setFieldNeutral(aadhaarInput, feedback, badge, "Pattern: 12 Digits (starts 2-9)");
            } else if (digits.length > 0 && (digits[0] === "0" || digits[0] === "1")) {
                setFieldInvalid(aadhaarInput, feedback, badge, "Valid Aadhaar cards cannot start with 0 or 1");
            } else if (digits.length === 12) {
                setFieldValid(aadhaarInput, feedback, badge, "✓ Valid 12-digit Aadhaar pattern");
            } else {
                setFieldInvalid(aadhaarInput, feedback, badge, `Enter ${12 - digits.length} more digit(s) (12 digits required)`);
            }
        });
    }

    // 4. Citizen Email Listener
    const emailInput = document.getElementById("citizenEmail");
    if (emailInput) {
        emailInput.addEventListener("input", () => {
            const val = emailInput.value.trim();
            const feedback = document.getElementById("citizenEmailFeedback");
            if (!val) {
                emailInput.className = "";
                feedback.className = "field-feedback";
                feedback.innerText = "";
            } else if (PATTERNS.email.test(val)) {
                emailInput.className = "is-valid";
                feedback.className = "field-feedback success";
                feedback.innerText = "✓ Valid email format";
            } else {
                emailInput.className = "is-invalid";
                feedback.className = "field-feedback error";
                feedback.innerText = "Invalid email structure (e.g., name@domain.com)";
            }
        });
    }

    // 5. Citizen Ward Listener
    const wardInput = document.getElementById("citizenWard");
    if (wardInput) {
        wardInput.addEventListener("input", () => {
            const val = wardInput.value.trim();
            const feedback = document.getElementById("citizenWardFeedback");
            if (!val) {
                wardInput.className = "";
                feedback.innerText = "";
            } else if (PATTERNS.ward.test(val)) {
                wardInput.className = "is-valid";
                feedback.className = "field-feedback success";
                feedback.innerText = "✓ Valid municipal ward format";
            } else {
                wardInput.className = "is-invalid";
                feedback.className = "field-feedback error";
                feedback.innerText = "Use format WARD-XX or digits 1-999 (e.g., WARD-12)";
            }
        });
    }

    // 6. Citizen PIN Code Listener
    const pinInput = document.getElementById("citizenPincode");
    if (pinInput) {
        pinInput.addEventListener("input", () => {
            pinInput.value = pinInput.value.replace(/\D/g, "").slice(0, 6);
            const val = pinInput.value;
            const feedback = document.getElementById("citizenPincodeFeedback");
            if (!val) {
                pinInput.className = "";
                feedback.innerText = "";
            } else if (PATTERNS.pincode.test(val)) {
                pinInput.className = "is-valid";
                feedback.className = "field-feedback success";
                feedback.innerText = "✓ Valid 6-digit postal PIN";
            } else {
                pinInput.className = "is-invalid";
                feedback.className = "field-feedback error";
                feedback.innerText = "Must be a 6-digit number starting with 1-9";
            }
        });
    }

    // 7. Department Code Listener (DEPT-[A-Z]{3}-\d{3})
    const deptCodeInput = document.getElementById("deptCode");
    if (deptCodeInput) {
        deptCodeInput.addEventListener("input", () => {
            let val = deptCodeInput.value.toUpperCase();
            deptCodeInput.value = val;
            const badge = document.getElementById("deptCodeBadge");
            const feedback = document.getElementById("deptCodeFeedback");

            if (!val) {
                setFieldNeutral(deptCodeInput, feedback, badge, "^DEPT-[A-Z]{3}-\\d{3}$");
            } else if (PATTERNS.deptCode.test(val)) {
                const sector = val.split("-")[1];
                const sectorName = SECTORS[sector] || "Custom Civic Sector";
                setFieldValid(deptCodeInput, feedback, badge, `✓ Valid: ${sector} (${sectorName})`);
            } else {
                setFieldInvalid(deptCodeInput, feedback, badge, "Format must strictly be DEPT-[SECTOR]-[NUM] (e.g. DEPT-WAT-101)");
            }
        });
    }

    // 8. Department Contact Listener
    const deptContactInput = document.getElementById("deptContact");
    if (deptContactInput) {
        deptContactInput.addEventListener("input", () => {
            deptContactInput.value = deptContactInput.value.replace(/\D/g, "").slice(0, 11);
            const val = deptContactInput.value;
            const feedback = document.getElementById("deptContactFeedback");
            if (!val) {
                deptContactInput.className = "";
                feedback.innerText = "";
            } else if (PATTERNS.deptContact.test(val)) {
                deptContactInput.className = "is-valid";
                feedback.className = "field-feedback success";
                feedback.innerText = "✓ Valid contact number";
            } else {
                deptContactInput.className = "is-invalid";
                feedback.className = "field-feedback error";
                feedback.innerText = "Must be a 10-digit mobile or municipal toll-free (e.g. 1800425104)";
            }
        });
    }
}

function setFieldValid(input, feedback, badge, text) {
    input.classList.remove("is-invalid");
    input.classList.add("is-valid");
    if (feedback) {
        feedback.className = "field-feedback success";
        feedback.innerText = text;
    }
    if (badge) {
        badge.className = "pattern-badge valid";
        badge.innerText = "VALID";
    }
}

function setFieldInvalid(input, feedback, badge, text) {
    input.classList.remove("is-valid");
    input.classList.add("is-invalid");
    if (feedback) {
        feedback.className = "field-feedback error";
        feedback.innerText = text;
    }
    if (badge) {
        badge.className = "pattern-badge invalid";
        badge.innerText = "INVALID";
    }
}

function setFieldNeutral(input, feedback, badge, defaultBadgeText) {
    input.classList.remove("is-valid", "is-invalid");
    if (feedback) {
        feedback.className = "field-feedback";
        feedback.innerText = "";
    }
    if (badge) {
        badge.className = "pattern-badge";
        badge.innerText = defaultBadgeText;
    }
}

// ---------------------------------------------------------
// DEPARTMENT ID SANDBOX TESTER
// ---------------------------------------------------------

function testDeptPatternSandbox() {
    const input = document.getElementById("sandboxDeptInput");
    const verdict = document.getElementById("sandboxVerdict");
    const expl = document.getElementById("sandboxExplanation");
    const val = input.value.trim().toUpperCase();

    if (PATTERNS.deptCode.test(val)) {
        verdict.className = "sandbox-verdict valid";
        verdict.innerText = "✓ VALID PATTERN";
        const parts = val.split("-");
        const secToken = parts[1];
        const unitToken = parts[2];
        const secName = SECTORS[secToken] || "Special Municipal Directorate";
        expl.innerHTML = `Parsed Sector: <strong>${secToken} (${secName})</strong> | Division Unit: <strong>${unitToken} (Division Unit ${unitToken})</strong>`;
    } else {
        verdict.className = "sandbox-verdict invalid";
        verdict.innerText = "✕ INVALID PATTERN";
        expl.innerHTML = `Pattern requires <code>DEPT-[A-Z]{3}-\\d{3}</code>. e.g. <strong>DEPT-WAT-101</strong> (Water), <strong>DEPT-ELE-102</strong> (Power).`;
    }
}

// ---------------------------------------------------------
// DATA FETCHING & SYNCHRONIZATION
// ---------------------------------------------------------

async function fetchAllData() {
    await Promise.allSettled([
        loadCitizens(),
        loadDepartments(),
        loadComplaints(),
        loadTelemetry()
    ]);
}

// 1. Load Citizens
async function loadCitizens() {
    try {
        const res = await fetch(`${API_BASE}/citizens`);
        if (!res.ok) throw new Error("Citizen service error");
        const citizens = await res.json();
        appState.citizens = citizens;

        // Update stats
        document.getElementById("statCitizens").innerText = citizens.length;
        document.getElementById("totalCitizensPill").innerText = citizens.length;
        document.getElementById("citizenCountBadge").innerText = citizens.length;

        renderCitizensTable(citizens);
    } catch (e) {
        console.warn("Unable to load citizens:", e);
        document.getElementById("citizensTableBody").innerHTML = `
            <tr><td colspan="6" class="loading-cell" style="color:var(--rose)">Citizen Service unavailable on port 5001.</td></tr>
        `;
    }
}

function renderCitizensTable(citizens) {
    const tbody = document.getElementById("citizensTableBody");
    if (!tbody) return;

    if (!citizens || citizens.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">No citizens registered yet.</td></tr>`;
        return;
    }

    tbody.innerHTML = citizens.map(c => `
        <tr>
            <td>
                <strong style="font-family:var(--font-mono); color:#818cf8; background:rgba(99,102,241,0.15); padding:3px 7px; border-radius:4px; border:1px solid rgba(99,102,241,0.3); font-size:11px;">
                    ${escapeHtml(c.citizen_code || "CIT-W01-" + c.citizen_id)}
                </strong>
                <span style="font-size:10px; color:var(--text-dim); margin-left:4px;">(#${c.citizen_id})</span>
            </td>
            <td><strong>${escapeHtml(c.name)}</strong></td>
            <td><span class="phone-tag">+91 ${escapeHtml(c.phone)}</span></td>
            <td><span class="aadhaar-tag">${escapeHtml(c.masked_aadhaar || c.aadhaar || "")}</span></td>
            <td><span class="ward-chip">${escapeHtml(c.ward)}</span></td>
            <td>
                <button class="btn-mini-action" onclick="fillCitizenInComplaint('${escapeHtml(c.citizen_code || c.citizen_id)}', '${escapeHtml(c.name)}')">
                    File Ticket
                </button>
            </td>
        </tr>
    `).join("");
}

function filterCitizens() {
    const q = document.getElementById("citizenSearchInput").value.toLowerCase();
    const filtered = appState.citizens.filter(c => 
        (c.name && c.name.toLowerCase().includes(q)) ||
        (c.phone && c.phone.includes(q)) ||
        (c.aadhaar && c.aadhaar.toLowerCase().includes(q)) ||
        (c.ward && c.ward.toLowerCase().includes(q))
    );
    renderCitizensTable(filtered);
}

// 2. Load Departments
async function loadDepartments() {
    try {
        const res = await fetch(`${API_BASE}/departments`);
        if (!res.ok) throw new Error("Department service error");
        const depts = await res.json();
        appState.departments = depts;

        document.getElementById("statDepartments").innerText = depts.length;
        document.getElementById("deptCountBadge").innerText = depts.length;

        renderDepartmentsGrid(depts);
        populateDeptDropdown();
        populateInspectorDropdown();
    } catch (e) {
        console.warn("Unable to load departments:", e);
        document.getElementById("departmentsGrid").innerHTML = `
            <div class="loading-cell" style="color:var(--rose)">Department Service unavailable on port 5005.</div>
        `;
    }
}

function renderDepartmentsGrid(depts) {
    const grid = document.getElementById("departmentsGrid");
    if (!grid) return;

    if (!depts || depts.length === 0) {
        grid.innerHTML = `<div class="loading-cell">No departments registered.</div>`;
        return;
    }

    grid.innerHTML = depts.map(d => `
        <div class="dept-card" onclick="selectDepartmentForInspect('${d.code || d.id}')">
            <div class="dept-card-top">
                <span class="dept-code-tag">${escapeHtml(d.code)}</span>
                <button class="btn-mini-action" onclick="event.stopPropagation(); selectDepartmentForInspect('${d.code || d.id}')">Inspect</button>
            </div>
            <h3>${escapeHtml(d.name)}</h3>
            <p>${escapeHtml(d.description || "Official municipal public utility and service operations.")}</p>
            <div class="dept-meta-row">
                <span>📞 ${escapeHtml(d.contact || "N/A")}</span>
                <span>👤 ${escapeHtml(d.head_officer || "Head Officer")}</span>
            </div>
        </div>
    `).join("");
}

function populateDeptDropdown() {
    const select = document.getElementById("complaintDeptSelect");
    if (!select) return;
    const currentVal = select.value;

    select.innerHTML = `<option value="">-- Select Responsible Department --</option>` +
        appState.departments.map(d => `
            <option value="${d.id}" data-code="${d.code}">${d.code} - ${d.name}</option>
        `).join("");

    if (currentVal) select.value = currentVal;
}

function populateInspectorDropdown() {
    const select = document.getElementById("inspectorDeptSelect");
    if (!select) return;
    select.innerHTML = `<option value="">-- Choose a Department --</option>` +
        appState.departments.map(d => `
            <option value="${d.code}">${d.code} - ${d.name}</option>
        `).join("");
}

// 3. Load Complaints
async function loadComplaints() {
    try {
        const filterStatus = document.getElementById("filterStatusSelect") ? document.getElementById("filterStatusSelect").value : "";
        let url = `${API_BASE}/complaints`;
        if (filterStatus) url += `?status=${filterStatus}`;

        const res = await fetch(url);
        if (!res.ok) throw new Error("Complaint service error");
        const complaints = await res.json();
        appState.complaints = complaints;

        const openCount = complaints.filter(c => c.status === "OPEN" || c.status === "IN_PROGRESS").length;
        document.getElementById("statComplaints").innerText = complaints.length;
        document.getElementById("statOpenComplaints").innerText = `${openCount} Open / Active`;
        document.getElementById("totalComplaintsPill").innerText = complaints.length;
        document.getElementById("complaintCountBadge").innerText = openCount;

        renderComplaintsTable(complaints);
    } catch (e) {
        console.warn("Unable to load complaints:", e);
        document.getElementById("complaintsTableBody").innerHTML = `
            <tr><td colspan="6" class="loading-cell" style="color:var(--rose)">Complaint Service unavailable. Start instances via Gateway.</td></tr>
        `;
    }
}

function renderComplaintsTable(complaints) {
    const tbody = document.getElementById("complaintsTableBody");
    if (!tbody) return;

    if (!complaints || complaints.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">No complaints logged yet.</td></tr>`;
        return;
    }

    tbody.innerHTML = complaints.map(c => `
        <tr>
            <td><strong style="font-family:var(--font-mono); color:#a5b4fc;">${escapeHtml(c.complaint_code || "#" + c.complaint_id)}</strong></td>
            <td>${escapeHtml(c.citizen_name || "Citizen #" + c.citizen_id)}</td>
            <td><span class="dept-code-tag">${escapeHtml(c.department_code || "DEPT-" + c.department_id)}</span></td>
            <td><span class="priority-tag ${(c.priority || 'medium').toLowerCase()}">${c.priority || 'MEDIUM'}</span></td>
            <td><span class="status-pill ${(c.status || 'open').toLowerCase()}">${c.status}</span></td>
            <td>
                <button class="btn-mini-action" onclick="viewComplaintInPipeline('${c.complaint_code || c.complaint_id}')">
                    Track
                </button>
            </td>
        </tr>
    `).join("");
}

// 4. Load Telemetry
async function loadTelemetry() {
    try {
        const res = await fetch(`${API_BASE}/instances`);
        if (!res.ok) throw new Error("Telemetry API error");
        const data = await res.json();
        const instances = data.instances || [];
        appState.instances = instances;

        document.getElementById("statInstances").innerText = instances.length;
        document.getElementById("instanceCountPill").innerText = instances.length;

        renderInstancesTable(instances);
    } catch (e) {
        console.warn("Unable to poll telemetry:", e);
    }
}

function renderInstancesTable(instances) {
    const tbody = document.getElementById("instancesTableBody");
    if (!tbody) return;

    if (!instances || instances.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="loading-cell">No active Complaint Service instances.</td></tr>`;
        return;
    }

    tbody.innerHTML = instances.map(inst => `
        <tr>
            <td><strong style="font-family:var(--font-mono); color:#a5b4fc;">:${inst.port}</strong></td>
            <td><span style="font-family:var(--font-mono)">${inst.pid || "PID-N/A"}</span></td>
            <td><span class="status-pill ${inst.healthy ? 'resolved' : 'open'}">${inst.healthy ? 'HEALTHY' : 'UNHEALTHY'}</span></td>
            <td><strong>${inst.active_requests || 0}</strong></td>
            <td>${inst.completed_requests || 0}</td>
            <td>${(inst.response_time_ms || 0).toFixed(1)} ms</td>
            <td>${(inst.cpu_percent || 0).toFixed(1)}%</td>
            <td><strong>${(inst.load_score || 0).toFixed(1)}</strong></td>
        </tr>
    `).join("");
}

function pollTelemetry() {
    loadTelemetry();
}

// ---------------------------------------------------------
// FORM SUBMISSION HANDLERS (WITH PATTERN MATCHING)
// ---------------------------------------------------------

// 1. Citizen Submission
async function handleCitizenSubmit(event) {
    event.preventDefault();
    const citizenCode = document.getElementById("citizenCodeInput") ? document.getElementById("citizenCodeInput").value.trim().toUpperCase() : "";
    const name = document.getElementById("citizenName").value.trim();
    const phone = document.getElementById("citizenPhone").value.trim();
    const aadhaar = document.getElementById("citizenAadhaar").value.trim();
    const email = document.getElementById("citizenEmail").value.trim();
    const ward = document.getElementById("citizenWard").value.trim();
    const pincode = document.getElementById("citizenPincode").value.trim();

    if (citizenCode && !PATTERNS.citizenCode.test(citizenCode)) {
        showToast("Citizen ID must match CIT-[WARD]-[TOKEN] (e.g. CIT-W12-89412)", "error");
        return;
    }
    // Client-side pattern check
    if (!PATTERNS.name.test(name)) {
        showToast("Full name must contain only letters, dots, and spaces (2-50 chars)", "error");
        return;
    }
    if (!PATTERNS.phone.test(phone)) {
        showToast("Phone number must be exactly 10 digits starting with 6, 7, 8, or 9", "error");
        return;
    }
    const cleanAadhaar = aadhaar.replace(/\s/g, "");
    if (!PATTERNS.aadhaarRaw.test(cleanAadhaar)) {
        showToast("Aadhaar must be 12 digits and cannot start with 0 or 1", "error");
        return;
    }

    btn.disabled = true;
    resultBox.style.display = "none";

    try {
        const response = await fetch(`${API_BASE}/citizens`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ citizen_code: citizenCode, name, phone, aadhaar, email, ward, pincode })
        });

        const data = await response.json();

        if (response.ok) {
            resultBox.className = "result-box success";
            resultBox.innerHTML = `
                <strong>✓ Citizen Onboarded Successfully!</strong><br>
                Citizen ID: <strong>${data.citizen_code}</strong> (DB #${data.citizen_id}) | Name: <strong>${data.name}</strong><br>
                Aadhaar: ${data.aadhaar} | Mobile: +91 ${data.phone}
            `;
            resultBox.style.display = "block";
            showToast(`Registered Citizen: ${data.citizen_code} (${data.name})`, "success");
            document.getElementById("citizenForm").reset();
            setupPatternListeners();
            loadCitizens();
        } else {
            resultBox.className = "result-box error";
            resultBox.innerHTML = `
                <strong>✕ Registration Failed:</strong> ${data.error}<br>
                ${data.field_errors ? Object.entries(data.field_errors).map(([k, v]) => `• ${v}`).join("<br>") : ""}
            `;
            resultBox.style.display = "block";
            showToast(data.error || "Citizen validation failed", "error");
        }
    } catch (e) {
        resultBox.className = "result-box error";
        resultBox.innerHTML = `<strong>✕ Network Error:</strong> Citizen Service is unavailable.`;
        resultBox.style.display = "block";
    } finally {
        btn.disabled = false;
    }
}

// 2. Department Submission
async function handleDepartmentSubmit(event) {
    event.preventDefault();
    const resultBox = document.getElementById("deptResultBox");
    const btn = document.getElementById("btnRegisterDept");

    const code = document.getElementById("deptCode").value.trim().toUpperCase();
    const name = document.getElementById("deptName").value.trim();
    const contact = document.getElementById("deptContact").value.trim();
    const email = document.getElementById("deptEmail").value.trim();
    const head = document.getElementById("deptHead").value.trim();
    const description = document.getElementById("deptDescription").value.trim();

    if (!PATTERNS.deptCode.test(code)) {
        showToast("Department ID must match DEPT-[SECTOR]-[NUM] (e.g. DEPT-WAT-101)", "error");
        return;
    }
    if (!PATTERNS.deptContact.test(contact)) {
        showToast("Contact must be 10 digits or municipal 1800 number", "error");
        return;
    }

    btn.disabled = true;
    resultBox.style.display = "none";

    try {
        const response = await fetch(`${API_BASE}/departments`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                code,
                name,
                contact,
                email,
                head_officer: head,
                description
            })
        });

        const data = await response.json();

        if (response.ok) {
            resultBox.className = "result-box success";
            resultBox.innerHTML = `
                <strong>✓ Department Created Successfully!</strong><br>
                Code: <strong>${data.department.code}</strong> | ID: <strong>#${data.department.id}</strong><br>
                Name: <strong>${data.department.name}</strong>
            `;
            resultBox.style.display = "block";
            showToast(`Created Department ${data.department.code}`, "success");
            document.getElementById("departmentForm").reset();
            loadDepartments();
        } else {
            resultBox.className = "result-box error";
            resultBox.innerHTML = `<strong>✕ Creation Failed:</strong> ${data.error}`;
            resultBox.style.display = "block";
            showToast(data.error || "Department validation failed", "error");
        }
    } catch (e) {
        resultBox.className = "result-box error";
        resultBox.innerHTML = `<strong>✕ Network Error:</strong> Department Service is unavailable.`;
        resultBox.style.display = "block";
    } finally {
        btn.disabled = false;
    }
}

// 3. Complaint Submission
async function handleComplaintSubmit(event) {
    event.preventDefault();
    const resultBox = document.getElementById("complaintResultBox");
    const btn = document.getElementById("btnSubmitComplaint");

    const citizenId = document.getElementById("complaintCitizenId").value.trim();
    const deptSelect = document.getElementById("complaintDeptSelect");
    const deptId = deptSelect.value;
    const selectedOption = deptSelect.options[deptSelect.selectedIndex];
    const deptCode = selectedOption ? selectedOption.getAttribute("data-code") : "";
    const priority = document.querySelector('input[name="priority"]:checked').value;
    const location = document.getElementById("complaintLocation").value.trim();
    const pincode = document.getElementById("complaintPincode").value.trim();
    const description = document.getElementById("complaintDescription").value.trim();

    if (!citizenId) {
        showToast("Please enter a registered Citizen ID", "error");
        return;
    }
    if (!deptId) {
        showToast("Please select the responsible Department", "error");
        return;
    }
    if (description.length < 10) {
        showToast("Description must be at least 10 characters long", "error");
        return;
    }

    btn.disabled = true;
    resultBox.style.display = "none";

    try {
        const response = await fetch(`${API_BASE}/complaints`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                citizen_id: citizenId,
                department_id: deptId,
                department_code: deptCode,
                priority,
                location,
                pincode,
                description
            })
        });

        const data = await response.json();

        if (response.ok) {
            resultBox.className = "result-box success";
            resultBox.innerHTML = `
                <strong>✓ Civic Grievance Logged Successfully!</strong><br>
                Tracking Token: <strong>${data.complaint_code}</strong> (ID #${data.complaint_id})<br>
                Citizen: <strong>${data.citizen_name}</strong> (${data.citizen_code || '#' + data.citizen_id}) &bull; Priority: <strong>${data.priority}</strong><br>
                Assigned to: <strong>${data.department_code || "Dept #" + data.department_id}</strong>
            `;
            resultBox.style.display = "block";
            showToast(`Complaint Logged: ${data.complaint_code}`, "success");
            document.getElementById("complaintForm").reset();
            document.getElementById("citizenNameTag").innerText = "";
            loadComplaints();
            // Automatically view in pipeline
            viewComplaintInPipeline(data.complaint_code);
        } else {
            resultBox.className = "result-box error";
            resultBox.innerHTML = `<strong>✕ Submission Failed:</strong> ${data.error}`;
            resultBox.style.display = "block";
            showToast(data.error || "Complaint submission failed", "error");
        }
    } catch (e) {
        resultBox.className = "result-box error";
        resultBox.innerHTML = `<strong>✕ Network Error:</strong> Complaint Service is unavailable.`;
        resultBox.style.display = "block";
    } finally {
        btn.disabled = false;
    }
}

// ---------------------------------------------------------
// COMPLAINT TRACKER & PIPELINE VISUALIZER
// ---------------------------------------------------------

async function trackComplaint() {
    const input = document.getElementById("searchTrackingInput");
    const query = input.value.trim();
    if (!query) {
        showToast("Please enter a Complaint ID or Tracking Code (e.g. CMP-2026-W8910)", "error");
        return;
    }
    await viewComplaintInPipeline(query);
}

async function viewComplaintInPipeline(identifier) {
    try {
        const res = await fetch(`${API_BASE}/complaints/${identifier}`);
        if (!res.ok) {
            showToast(`Complaint '${identifier}' not found in registry`, "error");
            return;
        }
        const data = await res.json();
        appState.currentComplaint = data;

        const pipeline = document.getElementById("trackingPipeline");
        pipeline.style.display = "block";

        document.getElementById("pipelineCode").innerText = data.complaint_code || `#${data.complaint_id}`;
        document.getElementById("pipelineStatusBadge").innerText = data.status;
        document.getElementById("pipelineStatusBadge").className = `pipeline-status-badge status-pill ${data.status.toLowerCase()}`;
        document.getElementById("step2Dept").innerText = data.department_code || `Dept #${data.department_id}`;

        // Update pipeline step circles
        const step1 = document.getElementById("step1");
        const step2 = document.getElementById("step2");
        const step3 = document.getElementById("step3");
        const step4 = document.getElementById("step4");

        [step1, step2, step3, step4].forEach(s => s.className = "pipe-step");

        if (data.status === "OPEN") {
            step1.classList.add("completed");
            step2.classList.add("active");
        } else if (data.status === "IN_PROGRESS") {
            step1.classList.add("completed");
            step2.classList.add("completed");
            step3.classList.add("active");
        } else if (data.status === "RESOLVED" || data.status === "CLOSED") {
            step1.classList.add("completed");
            step2.classList.add("completed");
            step3.classList.add("completed");
            step4.classList.add("completed");
        }

        document.getElementById("pipelineDetails").innerHTML = `
            <strong>Citizen:</strong> ${escapeHtml(data.citizen_name)} [${data.citizen_code || 'Citizen #' + data.citizen_id}]<br>
            <strong>Location:</strong> ${escapeHtml(data.location)} ${data.pincode ? `(PIN: ${data.pincode})` : ""}<br>
            <strong>Priority:</strong> <span class="priority-tag ${data.priority.toLowerCase()}">${data.priority}</span> | 
            <strong>Logged At:</strong> ${data.created_at || "Recent"}<br>
            <strong>Issue Details:</strong> "${escapeHtml(data.description)}"
        `;

        document.getElementById("quickStatusSelect").value = data.status;
        pipeline.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (e) {
        showToast("Error retrieving complaint details", "error");
    }
}

async function changeComplaintStatus() {
    if (!appState.currentComplaint) return;
    const newStatus = document.getElementById("quickStatusSelect").value;
    const id = appState.currentComplaint.complaint_id;

    try {
        const res = await fetch(`${API_BASE}/complaints/${id}/status`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus })
        });
        if (res.ok) {
            showToast(`Status updated to ${newStatus}`, "success");
            viewComplaintInPipeline(id);
            loadComplaints();
        } else {
            showToast("Failed to update status", "error");
        }
    } catch (e) {
        showToast("Error communicating with Complaint Service", "error");
    }
}

function fillCitizenInComplaint(citizenId, citizenName) {
    switchTab("complaints");
    document.getElementById("complaintCitizenId").value = citizenId;
    document.getElementById("citizenNameTag").innerText = `✓ ${citizenName}`;
}

async function verifyCitizenInComplaint() {
    const id = document.getElementById("complaintCitizenId").value.trim();
    const tag = document.getElementById("citizenNameTag");
    const feedback = document.getElementById("complaintCitizenFeedback");

    if (!id) {
        tag.innerText = "";
        feedback.className = "field-feedback";
        feedback.innerText = "Enter a valid ID from the Citizen Registry";
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/citizens/${id}`);
        if (res.ok) {
            const data = await res.json();
            tag.innerText = `✓ ${data.name} (${data.citizen_code || data.ward})`;
            feedback.className = "field-feedback success";
            feedback.innerText = `Verified Citizen: ${data.name} [${data.citizen_code || '#' + data.citizen_id}] | Phone: +91 ${data.phone}`;
        } else {
            tag.innerText = "";
            feedback.className = "field-feedback error";
            feedback.innerText = `Citizen ID #${id} not found in database`;
        }
    } catch (e) {
        tag.innerText = "";
    }
}

function updateDescCounter() {
    const len = document.getElementById("complaintDescription").value.length;
    document.getElementById("descCounter").innerText = `${len}/1000`;
}

// ---------------------------------------------------------
// DEPARTMENT INSPECTOR & ARCHITECTURE JUSTIFICATION
// ---------------------------------------------------------

function selectDepartmentForInspect(deptIdentifier) {
    const select = document.getElementById("inspectorDeptSelect");
    if (select) {
        select.value = deptIdentifier;
        inspectDepartment();
        document.getElementById("deptInspectorPanel").scrollIntoView({ behavior: "smooth" });
    }
}

async function inspectDepartment() {
    const select = document.getElementById("inspectorDeptSelect");
    const id = select.value;
    const container = document.getElementById("inspectorContent");
    if (!id) {
        container.innerHTML = `<div class="empty-state-notice">Select a department above or click "Inspect" on any department card.</div>`;
        return;
    }

    container.innerHTML = `<div class="loading-cell">Loading department complaints and citizen records...</div>`;

    try {
        const [deptRes, compRes, citRes] = await Promise.all([
            fetch(`${API_BASE}/departments/${id}`),
            fetch(`${API_BASE}/departments/${id}/complaints`),
            fetch(`${API_BASE}/departments/${id}/citizens`)
        ]);

        const dept = await deptRes.json();
        const complaintsData = compRes.ok ? await compRes.json() : { complaints: [] };
        const citizensData = citRes.ok ? await citRes.json() : { citizens: [] };

        const complaints = complaintsData.complaints || [];
        const citizens = citizensData.citizens || [];

        container.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
                <div>
                    <h3 style="color:#ffffff; font-size:16px; margin-bottom:4px;">${escapeHtml(dept.name)}</h3>
                    <span class="dept-code-tag" style="font-size:12px;">${dept.code}</span>
                    <span style="color:var(--text-muted); font-size:12px; margin-left:8px;">Chief: ${dept.head_officer} | Contact: ${dept.contact}</span>
                </div>
                <div style="display:flex; gap:12px;">
                    <span class="status-pill in_progress">${complaints.length} Assigned Complaints</span>
                    <span class="status-pill resolved">${citizens.length} Impacted Citizens</span>
                </div>
            </div>

            <h4 style="color:#e2e8f0; font-size:13px; margin: 12px 0 6px;">Live Complaints Assigned to ${dept.code}:</h4>
            ${complaints.length === 0 ? `<p style="color:var(--text-dim); font-size:12px;">No complaints currently active for this department.</p>` : `
                <div style="max-height:160px; overflow-y:auto; margin-bottom:14px;">
                    <table class="data-table">
                        <thead><tr><th>Code</th><th>Citizen</th><th>Location</th><th>Priority</th><th>Status</th></tr></thead>
                        <tbody>
                            ${complaints.map(c => `
                                <tr>
                                    <td><strong>${c.complaint_code || "#" + c.id}</strong></td>
                                    <td>${c.citizen_name || "Citizen #" + c.citizen_id}</td>
                                    <td>${c.location}</td>
                                    <td><span class="priority-tag ${c.priority ? c.priority.toLowerCase() : 'medium'}">${c.priority || 'MEDIUM'}</span></td>
                                    <td><span class="status-pill ${(c.status || 'open').toLowerCase()}">${c.status}</span></td>
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
                </div>
            `}
        `;
    } catch (e) {
        container.innerHTML = `<div class="loading-cell" style="color:var(--rose)">Error loading department details.</div>`;
    }
}

// Justification Modal
async function openJustificationModal() {
    const modal = document.getElementById("justificationModal");
    const body = document.getElementById("justificationModalBody");
    modal.classList.add("active");
    body.innerHTML = `<div class="loading-cell">Fetching technical justification schema...</div>`;

    try {
        const res = await fetch(`${API_BASE}/departments/justification`);
        const data = await res.json();

        body.innerHTML = `
            <div style="margin-bottom:20px;">
                <h4 style="color:#818cf8; font-family:var(--font-mono); font-size:18px; margin-bottom:8px;">
                    Pattern Specification: ${data.pattern}
                </h4>
                <p style="color:var(--text-muted); font-size:13px;">
                    Standard Reference: <strong>${data.canonical_example}</strong> (Water Supply Division 101)
                </p>
            </div>

            <h4 style="color:#ffffff; margin-bottom:12px;">1. Canonical Structure Decomposition</h4>
            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; margin-bottom:24px;">
                <div style="background:rgba(15,23,42,0.8); border:1px solid var(--border-subtle); padding:12px; border-radius:8px;">
                    <code style="color:#818cf8; font-size:14px; font-weight:700;">${data.structure_breakdown.prefix.token}</code>
                    <div style="color:#ffffff; font-weight:600; font-size:12px; margin-top:4px;">${data.structure_breakdown.prefix.meaning}</div>
                    <p style="color:var(--text-muted); font-size:11px; margin-top:4px;">${data.structure_breakdown.prefix.purpose}</p>
                </div>
                <div style="background:rgba(15,23,42,0.8); border:1px solid var(--border-subtle); padding:12px; border-radius:8px;">
                    <code style="color:#34d399; font-size:14px; font-weight:700;">${data.structure_breakdown.sector_code.token}</code>
                    <div style="color:#ffffff; font-weight:600; font-size:12px; margin-top:4px;">${data.structure_breakdown.sector_code.meaning}</div>
                    <p style="color:var(--text-muted); font-size:11px; margin-top:4px;">${data.structure_breakdown.sector_code.purpose}</p>
                </div>
                <div style="background:rgba(15,23,42,0.8); border:1px solid var(--border-subtle); padding:12px; border-radius:8px;">
                    <code style="color:#38bdf8; font-size:14px; font-weight:700;">${data.structure_breakdown.unit_code.token}</code>
                    <div style="color:#ffffff; font-weight:600; font-size:12px; margin-top:4px;">${data.structure_breakdown.unit_code.meaning}</div>
                    <p style="color:var(--text-muted); font-size:11px; margin-top:4px;">${data.structure_breakdown.unit_code.purpose}</p>
                </div>
            </div>

            <h4 style="color:#ffffff; margin-bottom:12px;">2. Architectural Pillars: Why This Pattern Was Chosen</h4>
            <div style="display:flex; flex-direction:column; gap:12px;">
                ${data.core_justifications.map(p => `
                    <div style="background:rgba(15,23,42,0.6); border-left:3px solid var(--primary); padding:10px 14px; border-radius:4px;">
                        <div style="color:#ffffff; font-weight:700; font-size:12px;">${p.pillar}</div>
                        <p style="color:var(--text-muted); font-size:12px; margin-top:3px;">${p.detail}</p>
                    </div>
                `).join("")}
            </div>
        `;
    } catch (e) {
        body.innerHTML = `<div class="loading-cell" style="color:var(--rose)">Failed to fetch justification schema.</div>`;
    }
}

function closeJustificationModal(event) {
    if (!event || event.target.id === "justificationModal" || event.target.className === "close-modal-btn") {
        document.getElementById("justificationModal").classList.remove("active");
    }
}

// ---------------------------------------------------------
// TELEMETRY & GATEWAY LOAD TESTER
// ---------------------------------------------------------

async function triggerGatewayLoadTest() {
    const duration = document.getElementById("loadDurationSlider").value;
    const consoleBox = document.getElementById("loadTestConsole");
    const output = document.getElementById("consoleOutput");
    const btn = document.getElementById("btnTriggerLoad");

    consoleBox.style.display = "block";
    btn.disabled = true;
    logToConsole(`[GATEWAY-LOAD] Dispatching simulated workload (Duration: ${duration}s) to /api/load-test...`);

    const start = performance.now();
    try {
        const res = await fetch(`${API_BASE}/load-test?duration=${duration}`);
        const data = await res.json();
        const elapsed = (performance.now() - start).toFixed(1);

        if (res.ok) {
            logToConsole(`[SUCCESS] Instance on port :${data.port} completed compute cycle in ${elapsed}ms.`);
            showToast(`Load test completed on port :${data.port}`, "success");
        } else {
            logToConsole(`[ERROR] ${data.error}`);
        }
        loadTelemetry();
    } catch (e) {
        logToConsole(`[ERROR] Gateway request timed out or failed: ${e.message}`);
    } finally {
        btn.disabled = false;
    }
}

async function triggerBurstLoadTest() {
    const consoleBox = document.getElementById("loadTestConsole");
    const btn = document.getElementById("btnTriggerBurst");

    consoleBox.style.display = "block";
    btn.disabled = true;
    logToConsole(`[BURST-TEST] Launching 5 concurrent stress requests to trigger auto-scaler threshold (>65%)...`);

    const requests = Array.from({ length: 5 }).map((_, idx) => {
        return fetch(`${API_BASE}/load-test?duration=3.0`)
            .then(r => r.json())
            .then(data => logToConsole(`[BURST-REQ #${idx + 1}] Handled by Complaint Instance :${data.port}`))
            .catch(err => logToConsole(`[BURST-REQ #${idx + 1}] Failed: ${err.message}`));
    });

    await Promise.allSettled(requests);
    logToConsole(`[BURST-COMPLETE] All burst requests settled. Polling gateway instance scaling...`);
    btn.disabled = false;
    loadTelemetry();
}

function logToConsole(msg) {
    const output = document.getElementById("consoleOutput");
    const line = document.createElement("div");
    line.innerText = `[${new Date().toLocaleTimeString()}] ${msg}`;
    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
}

// ---------------------------------------------------------
// TOAST NOTIFICATIONS & UTILS
// ---------------------------------------------------------

function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerText = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(30px)";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
