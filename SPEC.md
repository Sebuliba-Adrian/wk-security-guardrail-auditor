# SPEC.md — Module Specifications

---

## Module: file-parser

**INTENT:**
As a DevOps engineer, I want to upload any IaC file so that the system
can extract its resources without me knowing the parser internals.

**OUTCOMES:**
- Any valid .tf, .json, or .yaml IaC file produces a normalised resource list
- Any unsupported or malformed file produces a clear, safe error — never a crash

**SCOPE IN:**
- Terraform HCL2 (.tf)
- CloudFormation JSON (.json)
- CloudFormation YAML (.yaml, .yml)
- Empty files
- Malformed / invalid syntax files

**SCOPE OUT:**
- .toml, .hcl (non-Terraform), .tfvars
- Live cloud API scanning
- Files over 20 MB
- Multi-file Terraform modules (single file only)

**CONSTRAINTS:**
- Must never raise an unhandled exception
- Must return within 2 seconds for files under 1 MB
- No network calls

**ACCEPTANCE CRITERIA:**
- AC-01: Given a valid .tf file with 3 resources, When parsed, Then returns list of 3 resource dicts with type/name/config keys
- AC-02: Given a malformed .tf file, When parsed, Then returns ([], parse_error=True) without raising
- AC-03: Given an empty file, When parsed, Then returns ([], parse_error=False)
- AC-04: Given a valid CloudFormation JSON, When parsed, Then returns normalised resource list
- AC-05: Given a valid CloudFormation YAML, When parsed, Then returns normalised resource list
- AC-06: Given a .py file, When parsed, Then raises ValueError("unsupported extension")

**VERIFICATION:**
`pytest tests/unit/test_parser.py -v`

---

## Module: scanner-engine

**INTENT:**
As a security engineer, I want every uploaded resource checked against all
12 rules so that no misconfiguration is silently missed.

**OUTCOMES:**
- Every resource is evaluated against every applicable rule
- Each finding includes rule ID, severity, title, description, and remediation
- Clean files produce zero findings

**SCOPE IN:**
- All 12 rules (see ARCHITECTURE.md)
- Both Terraform and CloudFormation resource formats
- Resources with missing or partial configuration keys

**SCOPE OUT:**
- Custom rule authoring
- Rule suppression / ignore lists
- Cross-resource relationship analysis

**CONSTRAINTS:**
- No finding on a resource with missing keys (graceful skip, never raise)
- Deterministic output — same input always produces same findings

**ACCEPTANCE CRITERIA:**
- AC-01: Given aws_s3_bucket with acl="public-read", When scanned, Then S3_PUBLIC_ACL CRITICAL finding returned
- AC-02: Given aws_s3_bucket with acl="private", When scanned, Then no finding
- AC-03: Given security_group_rule with port 22 and cidr 0.0.0.0/0, When scanned, Then SSH_OPEN_TO_WORLD CRITICAL finding
- AC-04: Given security_group_rule with port 22 and cidr 10.0.0.0/8, When scanned, Then no finding
- AC-05: Given resource dict with missing keys, When scanned, Then no finding and no exception
- AC-06: Given clean file with no violations, When scanned, Then empty findings list
- AC-07: Each of the 12 rules fires correctly on crafted input (parametrised)
- AC-08: Each of the 12 rules does NOT fire on compliant input (parametrised)

**VERIFICATION:**
`pytest tests/unit/test_scanner.py -v`

---

## Module: risk-scorer

**INTENT:**
As a manager, I want a single 0–100 risk score so that I can understand
infrastructure risk without reading individual findings.

**OUTCOMES:**
- Score of 0 for clean scans
- Score reflects severity composition correctly
- Score never exceeds 100 regardless of finding count

**SCOPE IN:**
- CRITICAL, HIGH, MEDIUM severity findings
- Any number of findings (0 to N)

**SCOPE OUT:**
- LOW severity (excluded from score to keep signal clean)
- Weighted scoring by resource type

**CONSTRAINTS:**
- Formula must be deterministic and auditable
- No external dependencies

**ACCEPTANCE CRITERIA:**
- AC-01: Given 0 findings, When scored, Then score = 0
- AC-02: Given 1 CRITICAL finding, When scored, Then score = 40
- AC-03: Given 1 HIGH finding, When scored, Then score = 20
- AC-04: Given 1 MEDIUM finding, When scored, Then score = 5
- AC-05: Given 3 CRITICAL findings, When scored, Then score = 100 (capped)
- AC-06: Given 2 CRITICAL + 1 HIGH, When scored, Then score = min(80+20, 100) = 100
- AC-07: Given 1 CRITICAL + 1 MEDIUM, When scored, Then score = 45

**VERIFICATION:**
`pytest tests/unit/test_scorer.py -v`

---

## Module: api-routes

**INTENT:**
As a developer, I want a clean REST API so that I can integrate the scanner
into any CI/CD pipeline or tool.

**OUTCOMES:**
- File upload triggers async scan with immediate 202 response
- Results retrievable by scan ID
- All error cases return correct HTTP status codes

**SCOPE IN:**
- POST /api/scan (upload + enqueue)
- GET /api/scan/{scan_id} (get results)
- GET /api/scans (history, last 50)
- GET /api/health

**SCOPE OUT:**
- Authentication / authorisation
- Rate limiting (deferred)
- Webhooks / callbacks
- Streaming scan results

**CONSTRAINTS:**
- POST /api/scan must respond within 500ms (before scan runs)
- File field name must be "file"
- Max file size: 20 MB

**ACCEPTANCE CRITERIA:**
- AC-01: Given valid .tf upload, When POST /api/scan, Then 202 with {scan_id, status="queued"}
- AC-02: Given .py upload, When POST /api/scan, Then 415
- AC-03: Given no file in request, When POST /api/scan, Then 422
- AC-04: Given valid scan_id, When GET /api/scan/{id}, Then 200 with full result
- AC-05: Given unknown scan_id, When GET /api/scan/{id}, Then 404
- AC-06: Given empty database, When GET /api/scans, Then 200 with empty list
- AC-07: GET /api/health returns 200 with {status: "ok"}
- AC-08: Scan result contains: scan_id, filename, status, risk_score, findings[], summary, scanned_at

**VERIFICATION:**
`pytest tests/integration/test_api.py -v`

---

## Module: dashboard

**INTENT:**
As a security manager, I want a visual dashboard so that I can understand
risk at a glance without reading raw JSON.

**OUTCOMES:**
- Single HTML page renders correctly in browser
- Risk gauge immediately communicates severity
- Charts update with each page load (no WebSocket required)

**SCOPE IN:**
- Risk score gauge (doughnut, colour-coded)
- Findings by severity (bar chart)
- Top rules triggered (horizontal bar)
- Recent scans table (last 10, clickable)
- Empty state when no scans exist

**SCOPE OUT:**
- Real-time updates / WebSocket
- User authentication
- Export to PDF
- Mobile-responsive layout

**CONSTRAINTS:**
- No external CDN calls (Chart.js bundled inline)
- Must render correctly with 0 scans (empty state)
- Must render correctly with 1 scan
- Must render correctly with 50 scans

**ACCEPTANCE CRITERIA:**
- AC-01: GET /dashboard returns 200 with HTML containing "Risk Score"
- AC-02: Dashboard renders with 0 scans (empty state message visible)
- AC-03: Dashboard renders with scan data (charts initialised)
- AC-04: Risk gauge colour matches score band (green/amber/red)
- AC-05: No external network requests made by the page

**VERIFICATION:**
Manual browser check + `pytest tests/smoke/test_dashboard.py -v`
