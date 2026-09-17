# Civic Microservices: Pattern Matching, Production-Grade UI Redesign & Department ID Architecture

This plan covers implementing strict regex-based pattern matching across the entire civic microservices application, modernizing the frontend into a responsive, production-grade municipal administration portal, creating a dedicated multi-page layout with department management, and formalizing the Department ID architectural pattern with exhaustive technical justifications.

---

## User Review Required

> [!IMPORTANT]
> **Key Pattern Standards to be Enforced Across Backend & Frontend:**
> 1. **Citizen Phone**: Exactly 10 digits starting with [6-9] (`^[6-9]\d{9}$`). Rejects non-digits, alphabets, or improper lengths.
> 2. **Aadhaar Number**: 12 digits formatted as `XXXX XXXX XXXX` (`^[2-9]\d{3}\s?\d{4}\s?\d{4}$`), first digit between 2–9, with auto-masking and format verification.
> 3. **Department ID**: Structured municipal code `^DEPT-[A-Z]{3}-\d{3}$` (e.g., `DEPT-WAT-101` for Water Supply, `DEPT-ELE-102` for Electricity, `DEPT-ROA-103` for Roads).
> 4. **PIN Code**: 6-digit Indian Postal PIN (`^[1-9]\d{5}$`).
> 5. **Email**: RFC 5322 compliant regex (`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`).
> 6. **Ward Identifier**: Standard municipal format (`^WARD-\d{1,3}$` or `^\d{1,3}$`).
> 7. **Complaint Tracking Code**: `^CMP-\d{4}-[A-Z0-9]{5}$`.

---

## Proposed Architectural Changes

### 1. Backend Pattern Matching & Data Schema Upgrades

#### Citizen Service (`citizen-service/backend/app.py`)
- **Schema Migration**: Add `aadhaar`, `email`, `pincode`, and `created_at` columns to `citizens` SQLite database with automatic migration for existing tables.
- **Pattern Validation (Server-side)**:
  - Phone: `re.match(r"^[6-9]\d{9}$", phone)`
  - Aadhaar: `re.match(r"^[2-9]\d{3}\s?\d{4}\s?\d{4}$", aadhaar)` or 12 continuous digits `^[2-9]\d{11}$`
  - Name: `re.match(r"^[A-Za-z\s.]{2,50}$", name)`
  - Pincode: `re.match(r"^[1-9]\d{5}$", pincode)`
  - Email: Standard email regex
- Return standard HTTP 400 with granular field-level validation errors.
- Pre-seed realistic initial citizen records with verified valid IDs.

#### Department Service (`department-service/backend/app.py`)
- **Schema Migration**: Add `code` (e.g. `DEPT-WAT-101`), `email`, `head_officer`, `category`, and `operating_hours` to `departments` SQLite database.
- **Pattern Validation (Server-side)**:
  - Department Code: `re.match(r"^DEPT-[A-Z]{3}-\d{3}$", code)`
  - Contact Phone: `re.match(r"^(1800\d{6,7}|[6-9]\d{9})$", contact)`
  - Email: `re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email)`
  - Name: `re.match(r"^[A-Za-z0-9\s&,-]{3,60}$", name)`
- Allow querying by both numeric `id` and structured `code` (e.g. `GET /departments/DEPT-WAT-101`).
- Pre-seed essential civic departments (Water Supply, Electricity, Roads, Sanitation, Health, Revenue, Disaster Management, Urban Planning).

#### Complaint Service (`complaint-service/backend/app.py`)
- **Schema Migration**: Add `complaint_code`, `priority` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), `pincode`, and `created_at` to `complaints` table.
- **Pattern Validation (Server-side)**:
  - Description: Min 10, max 1000 characters; reject unsafe script characters.
  - Priority: Enum validation.
  - Department ID: Support both numeric ID and structured code lookup.
  - Location: Sanitized alphanumeric string with minimum length.

#### API Gateway (`api-gateway/app.py`)
- Serve the unified production web application and static assets at `/` or `/portal`.
- Route support for department code lookups (`/api/departments/<string_or_int:dept_id>`).
- Preserve existing load-balancing, auto-scaling, and telemetry functionality.

---

### 2. Department ID Pattern & Deep Technical Justification

The Department ID follows the strict canonical standard:
$$\mathbf{DEPT}\text{ - }\mathbf{[A\text{-}Z]\{3\}}\text{ - }\mathbf{\backslash d\{3\}}$$
*Example*: `DEPT-WAT-101` (Water Supply Division 101), `DEPT-ELE-102` (Electricity Grid unit 102).

#### The 5 Architectural Pillars of Justification (included in interactive UI and documentation):
1. **Semantic Human-Readability & Zero-Ambiguity**:
   - Raw integer IDs like `3` or `12` are opaque and error-prone during emergency triage or manual dispatch.
   - `DEPT-WAT-101` instantly informs dispatchers, field engineers, and citizens of the exact jurisdiction without querying lookup tables.
2. **Gateway-Level Regex Routing & Zero-DB Triage**:
   - In microservice networks, the API Gateway or message broker (RabbitMQ/Kafka) can extract the sector mnemonic (`[WAT]`, `[ELE]`) with a single fast regex and route complaints to specific service queues or partitioned instances without incurring database lookup latency.
3. **Collision Resistance Across Civic Jurisdictions**:
   - As cities scale or merge municipalities (e.g., Greater Bengaluru Municipal Corporation or Delhi NCR), numeric auto-increment keys inevitably collide. Prefix-namespaced keys guarantee uniqueness across multi-zone database federation.
4. **National E-Governance & ISO Alignment**:
   - Conforms with modern municipal data taxonomy guidelines (such as India's National Urban Digital Mission / DIGIT framework and ISO 3166-2 division codes) for municipal service classifications.
5. **Structured Telemetry & Log Aggregation**:
   - Monitoring platforms (ELK stack, Prometheus, Datadog) can automatically group API error rates, latency spikes, and civic complaint surges by sector token (`WAT`, `ELE`, `ROA`) without payload inspection.

---

### 3. Production-Grade Frontend Design & Multi-Page Layout

#### Visual Design System
- **Theme**: Curated dark & light modern glassmorphic municipal dashboard (slate `#0b1329`, dark indigo `#0f172a`, accent indigo `#6366f1`, emerald `#10b981`, amber `#f59e0b`, rose `#ef4444`).
- **Typography**: Inter / Plus Jakarta Sans via Google Fonts, crisp monospace font for IDs and code patterns.
- **Micro-Interactions**: Smooth card hover effects, real-time input status glow (valid green / invalid red), animated tabs, live stats counters.
- **Interactive Pattern Feedback**: Live regex validator on each input showing checkmark/cross, character counter, input masking (Aadhaar `XXXX XXXX XXXX`, phone `+91 XXXXX XXXXX`), and explanation tooltip.

#### Multi-Page Navigation Layout
The frontend will feature an application shell with a persistent top bar (system status, live gateway indicator, current time) and intuitive tabbed page routing:

1. **Dashboard Page (`#overview`)**:
   - System Health, Gateway Telemetry, active Complaint Service instances, CPU load score.
   - Microservices Architecture Flowchart / Topology map.
   - Key metrics: Total Citizens Registered, Departments Active, Open Complaints, Scaling status.
2. **Citizen Portal Page (`#citizens`)**:
   - Register Citizen Form with live pattern verification (Name, 10-digit Phone, 12-digit Aadhaar, Email, Ward, PIN).
   - Citizen Directory with instant search by ID, phone, or Aadhaar, and detail drawer.
3. **Department Hub Page (`#departments`)**:
   - Department Directory across 8 municipal sectors (Water, Electricity, Roads, Sanitation, Health, Revenue, Disaster Response, Urban Planning).
   - Add New Department Form enforcing `DEPT-[A-Z]{3}-\d{3}` with real-time sector decoder.
   - **Interactive Department ID Architecture & Justification Panel**:
     - Interactive Regex Dissecting Visualizer (explaining Prefix, Sector Code, and Unit).
     - Full 5-pillar technical rationale breakdown.
     - Live Pattern Sandbox: Enter any Department ID to test against municipal regex and see immediate parsing.
   - Department Drilldown: View staff, hotline, and live complaints linked to the department.
4. **Complaint Resolution Center Page (`#complaints`)**:
   - File Civic Complaint Form (Citizen verification, Department selection, Priority pill selector, Location with PIN, Description).
   - Live Tracking Pipeline (Submitted → Dispatched → Inspection → In Progress → Resolved).
   - Filterable Complaints Table with status badges and search.
5. **Gateway & Telemetry Console Page (`#telemetry`)**:
   - Gateway load test trigger with duration slider (`/api/load-test`).
   - Live monitor for auto-scaler (MIN 1 to MAX 6 instances) showing dynamic PIDs, ports, CPU, response times.

#### Synchronization
- Update individual service frontends (`citizen-service/frontend`, `complaint-service/frontend`, `department-service/frontend`) with upgraded styling and pattern matching for standalone usage.
- Provide the unified master production application directly via the API Gateway (`api-gateway/portal/index.html`, `script.js`, `style.css`), accessible on `http://127.0.0.1:5000/`.

---

## Verification Plan

### Automated & Programmatic Verification
1. **Backend Pattern Validation Test Script**:
   - Test invalid phone (<10 digits, >10 digits, starts with 1-5, alphabetic) -> expect 400 Bad Request.
   - Test valid phone (10 digits starting with 6-9) -> expect 201/200 Success.
   - Test invalid Aadhaar (<12 digits, starts with 0 or 1, letters) -> expect 400 Bad Request.
   - Test valid Aadhaar (12 digits, formatted or raw) -> expect 201/200 Success.
   - Test invalid Department ID (`DEPT123`, `DEPT-WATER-1`, `123`) -> expect 400 Bad Request.
   - Test valid Department ID (`DEPT-WAT-101`, `DEPT-ELE-102`) -> expect 201/200 Success.
   - Test invalid Email, Pincode -> expect 400.
2. **Service-to-Service Integration**:
   - Ensure complaint creation verifies citizen and department correctly.
   - Ensure Department complaints and citizens endpoints function properly.
3. **Gateway Load & Scaling**:
   - Run a test request through `/api/load-test` and verify response.

### Interactive Browser Verification
- Use `browser_subagent` to open `http://127.0.0.1:5000/` in the browser.
- Verify visual aesthetics, tab switching, dark theme, and typography.
- Test form input interactions:
  - Type invalid phone -> verify red pattern validation warning.
  - Type valid 10-digit phone -> verify green validation badge.
  - Type Aadhaar -> verify auto-formatting and validation badge.
  - Navigate to Department Hub -> inspect the Department ID Justification panel and interactive sandbox.
  - Submit citizen, department, and complaint, checking real-time response.
- Capture screenshot / recording of the production UI for the walkthrough.
