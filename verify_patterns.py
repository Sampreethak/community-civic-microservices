import unittest
import requests
import json
import time
import subprocess
import sys
import os

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# URLs
GATEWAY_URL = "http://127.0.0.1:5000"
CITIZEN_URL = "http://127.0.0.1:5001"
DEPARTMENT_URL = "http://127.0.0.1:5005"

class TestPatternMatchingAndServices(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 60)
        print("RUNNING PATTERN MATCHING & MICROSERVICES TEST SUITE")
        print("=" * 60)

    # -----------------------------------------------------
    # 1. CITIZEN PATTERN VALIDATION
    # -----------------------------------------------------
    def test_01_citizen_phone_pattern_invalid_length(self):
        """Rejects phone numbers that are not 10 digits."""
        payload = {
            "name": "Test Citizen",
            "phone": "984512345", # 9 digits
            "aadhaar": "2345 6789 0123",
            "ward": "WARD-01"
        }
        res = requests.post(f"{CITIZEN_URL}/citizens", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertIn("phone", data.get("field_errors", {}))
        print("âœ“ Citizen rejected 9-digit phone")

    def test_02_citizen_phone_pattern_invalid_start_digit(self):
        """Rejects phone numbers not starting with 6, 7, 8, or 9."""
        payload = {
            "name": "Test Citizen",
            "phone": "1234567890", # Starts with 1
            "aadhaar": "2345 6789 0123",
            "ward": "WARD-01"
        }
        res = requests.post(f"{CITIZEN_URL}/citizens", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("phone", res.json().get("field_errors", {}))
        print("âœ“ Citizen rejected phone starting with invalid digit '1'")

    def test_03_citizen_aadhaar_pattern_invalid_start_digit(self):
        """Rejects Aadhaar starting with 0 or 1."""
        payload = {
            "name": "Test Citizen",
            "phone": "9845123450",
            "aadhaar": "0123 4567 8901", # Starts with 0
            "ward": "WARD-01"
        }
        res = requests.post(f"{CITIZEN_URL}/citizens", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("aadhaar", res.json().get("field_errors", {}))
        print("âœ“ Citizen rejected Aadhaar starting with '0'")

    def test_04_citizen_aadhaar_pattern_invalid_length(self):
        """Rejects Aadhaar with improper digit count."""
        payload = {
            "name": "Test Citizen",
            "phone": "9845123451",
            "aadhaar": "2345 6789 01", # 10 digits instead of 12
            "ward": "WARD-01"
        }
        res = requests.post(f"{CITIZEN_URL}/citizens", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("aadhaar", res.json().get("field_errors", {}))
        print("âœ“ Citizen rejected 10-digit Aadhaar")

    def test_05_citizen_valid_registration(self):
        """Accepts strictly valid 10-digit phone and 12-digit Aadhaar."""
        payload = {
            "name": "Arjun Singhania",
            "phone": "9898765432",
            "aadhaar": "3456 7890 1234",
            "email": "arjun.singhania@civic.org",
            "ward": "WARD-18",
            "pincode": "560034"
        }
        res = requests.post(f"{CITIZEN_URL}/citizens", json=payload)
        self.assertIn(res.status_code, [201, 409])
        if res.status_code == 201:
            data = res.json()
            self.assertEqual(data["phone"], "9898765432")
            self.assertEqual(data["aadhaar"], "3456 7890 1234")
            self.assertTrue(data["citizen_code"].startswith("CIT-"))
            print(f"[PASS] Valid citizen registered with auto-generated Citizen ID: {data['citizen_code']}")
        else:
            print("[PASS] Citizen duplicate handling verified (409 Conflict)")

    def test_05b_citizen_id_invalid_pattern(self):
        """Rejects custom Citizen ID not conforming to CIT-[WARD]-[TOKEN]."""
        payload = {
            "citizen_code": "INVALID_ID_9999",
            "name": "Invalid Citizen ID Test",
            "phone": "9898765499",
            "aadhaar": "3456 7890 9999",
            "ward": "WARD-01"
        }
        res = requests.post(f"{CITIZEN_URL}/citizens", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("citizen_code", res.json().get("field_errors", {}))
        print("[PASS] Citizen Service rejected invalid Citizen ID pattern 'INVALID_ID_9999'")

    def test_05c_citizen_id_valid_custom_pattern(self):
        """Accepts compliant custom Citizen ID conforming to CIT-[WARD]-[TOKEN]."""
        payload = {
            "citizen_code": "CIT-W18-98451",
            "name": "Meera Natarajan",
            "phone": "9898765433",
            "aadhaar": "3456 7890 5678",
            "email": "meera.natarajan@civic.org",
            "ward": "WARD-18",
            "pincode": "560034"
        }
        res = requests.post(f"{CITIZEN_URL}/citizens", json=payload)
        self.assertIn(res.status_code, [201, 409])
        print("[PASS] Citizen Service accepted compliant Citizen ID 'CIT-W18-98451'")

    def test_05d_citizen_lookup_by_code(self):
        """Verifies citizen lookup using the canonical Citizen ID code."""
        res = requests.get(f"{CITIZEN_URL}/citizens/CIT-W18-98451")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["citizen_code"], "CIT-W18-98451")
        print(f"[PASS] Citizen lookup verified via structured code: {data['citizen_code']} ({data['name']})")

    def test_05e_citizen_justification_api(self):
        """Verifies the Citizen ID Architecture Justification API."""
        res = requests.get(f"{CITIZEN_URL}/citizens/justification")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("pattern", data)
        self.assertIn("structure_breakdown", data)
        self.assertIn("core_justifications", data)
        print("[PASS] Citizen ID Justification API returns architecture rationale")

    # -----------------------------------------------------
    # 2. DEPARTMENT PATTERN & JUSTIFICATION
    # -----------------------------------------------------
    def test_06_department_id_invalid_pattern(self):
        """Rejects Department ID that does not conform to DEPT-[A-Z]{3}-\\d{3}."""
        payload = {
            "code": "INVALID_CODE_123",
            "name": "Test Division",
            "contact": "9845011009"
        }
        res = requests.post(f"{DEPARTMENT_URL}/departments", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("code", res.json().get("field_errors", {}))
        print("âœ“ Department Service rejected non-compliant ID pattern 'INVALID_CODE_123'")

    def test_07_department_id_valid_pattern(self):
        """Accepts compliant DEPT-[A-Z]{3}-\\d{3} pattern."""
        payload = {
            "code": "DEPT-URB-201",
            "name": "Urban Mobility & Bus Rapid Transit",
            "contact": "9845011201",
            "email": "urbanmobility@civic.gov.in",
            "description": "Rapid transit bus lanes and pedestrian infrastructure."
        }
        res = requests.post(f"{DEPARTMENT_URL}/departments", json=payload)
        self.assertIn(res.status_code, [201, 409])
        print("âœ“ Department Service accepted compliant DEPT-URB-201 code")

    def test_08_department_justification_api(self):
        """Verifies the Department ID Architecture Justification API."""
        res = requests.get(f"{DEPARTMENT_URL}/departments/justification")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("pattern", data)
        self.assertIn("structure_breakdown", data)
        self.assertIn("core_justifications", data)
        self.assertEqual(len(data["core_justifications"]), 5)
        print("âœ“ Department ID Justification API returns all 5 architectural pillars")

    # -----------------------------------------------------
    # 3. COMPLAINT SERVICE & GATEWAY INTEGRATION
    # -----------------------------------------------------
    def test_09_complaint_short_description_rejected(self):
        """Rejects complaint descriptions shorter than 10 characters."""
        payload = {
            "citizen_id": 1,
            "department_id": "1",
            "description": "Too short", # 9 chars
            "location": "MG Road"
        }
        res = requests.post(f"{GATEWAY_URL}/api/complaints", json=payload)
        self.assertEqual(res.status_code, 400)
        print("âœ“ Complaint Service rejected description < 10 characters")

    def test_10_complaint_valid_submission_generates_tracking_token(self):
        """Accepts valid complaint and generates CMP-YYYY-XXXXX tracking code."""
        payload = {
            "citizen_id": 1,
            "department_code": "DEPT-WAT-101",
            "description": "Potable water supply line broken near main intersection.",
            "location": "Main 80ft Road, Ward 12",
            "priority": "HIGH"
        }
        res = requests.post(f"{GATEWAY_URL}/api/complaints", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertTrue(data["complaint_code"].startswith("CMP-2026-"))
        self.assertEqual(data["priority"], "HIGH")
        print(f"âœ“ Complaint successfully created with tracking token: {data['complaint_code']}")

    def test_11_gateway_serves_html_portal(self):
        """Verifies API Gateway serves the production portal HTML at / and /portal."""
        res = requests.get(f"{GATEWAY_URL}/portal")
        self.assertEqual(res.status_code, 200)
        self.assertIn("SmartCivic 360", res.text)
        self.assertIn("Department Hub & ID Architecture", res.text)
        print("âœ“ Gateway cleanly serves unified portal HTML at /portal")

    def test_12_gateway_load_test_and_telemetry(self):
        """Verifies /api/load-test and instance telemetry polling."""
        res = requests.get(f"{GATEWAY_URL}/api/load-test?duration=0.5")
        self.assertEqual(res.status_code, 200)
        telemetry = requests.get(f"{GATEWAY_URL}/api/instances").json()
        self.assertGreaterEqual(telemetry["instance_count"], 1)
        print(f"âœ“ Gateway load-balancing verified ({telemetry['instance_count']} active instance(s))")


if __name__ == "__main__":
    unittest.main()
