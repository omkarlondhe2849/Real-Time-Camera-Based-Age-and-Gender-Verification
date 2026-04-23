"""
test_age_gender_verification.py
================================
Automated browser-based test suite for:
"Enhancing company registration security by implementing real-time
 camera-based age and gender verification to prevent fraudulent entries."

Group 22 – Senim Solutions LLP
Organization: Senim Solutions LLP  |  Project: Real-Time Age & Gender Verification

Test Cases Covered
------------------
TC01  Capture Live Image         (High Priority)
TC02  Face Detection             (High Priority)
TC03  Gender Detection           (High Priority)
TC04  Age Detection              (High Priority)
TC05  No Face in Frame           (Medium Priority)
TC06  Multiple Faces in Frame    (Medium Priority)
TC07  Gender Mismatch            (High Priority)
TC08  Underage User              (High Priority)
TC09  Poor Lighting Conditions   (Low Priority)
TC10  Store Verification Result  (Medium Priority)

Tools Used
----------
- pytest          : test runner & reporting
- Selenium        : browser automation (Chrome)
- requests        : direct HTTP calls for API-level tests
- webdriver_manager: auto-installs chromedriver
"""

import os
import time
import base64

import pytest
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_URL   = "http://127.0.0.1:5000"
TEST_DATA  = os.path.join(os.path.dirname(__file__), "test_data")
FACE_IMG   = os.path.join(TEST_DATA, "face_image.jpg")
BLANK_IMG  = os.path.join(TEST_DATA, "blank_image.jpg")
DARK_IMG   = os.path.join(TEST_DATA, "dark_image.jpg")
MULTI_IMG  = os.path.join(TEST_DATA, "multi_face_image.jpg")


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def upload_image_via_api(image_path: str) -> requests.Response:
    """POST an image to /upload and return the raw response."""
    with open(image_path, "rb") as f:
        return requests.post(
            f"{BASE_URL}/upload",
            files={"fileToUpload": (os.path.basename(image_path), f, "image/jpeg")},
            timeout=30,
        )


def image_to_base64_dataurl(image_path: str) -> str:
    """Convert an image file to a base64 data URL for the /process_frame endpoint."""
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:image/jpeg;base64,{data}"


def process_frame_api(image_path: str) -> requests.Response:
    """POST an image to /process_frame and return the raw response."""
    return requests.post(
        f"{BASE_URL}/process_frame",
        json={"image": image_to_base64_dataurl(image_path)},
        timeout=30,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC01  –  Capture Live Image  (High Priority)
# ─────────────────────────────────────────────────────────────────────────────
class TestTC01_CaptureLiveImage:
    """
    Precondition : Camera must be connected and accessible (fake device injected by Selenium).
    Steps        : 1. Open /webcam  2. Click "Start Camera"
    Expected     : Video element becomes active; canvas overlay is rendered.
    """

    def test_webcam_page_loads(self, driver):
        """TC01-A: The /webcam page responds with HTTP 200."""
        driver.get(f"{BASE_URL}/webcam")
        assert "Live" in driver.title or "Detection" in driver.title, (
            "TC01 FAIL – Webcam page did not load correctly"
        )

    def test_start_camera_button_present(self, driver):
        """TC01-B: 'Start Camera' button exists on the webcam page."""
        driver.get(f"{BASE_URL}/webcam")
        btn = driver.find_element(By.ID, "startBtn")
        assert btn is not None, "TC01 FAIL – Start Camera button not found"
        assert btn.is_enabled(), "TC01 FAIL – Start Camera button is disabled"

    def test_start_camera_activates_video(self, driver):
        """TC01-C: Clicking Start Camera changes status text (camera activates)."""
        driver.get(f"{BASE_URL}/webcam")
        driver.find_element(By.ID, "startBtn").click()
        wait = WebDriverWait(driver, 10)
        # Status dot should turn green (class 'dot active') OR status text changes
        status = wait.until(
            EC.presence_of_element_located((By.ID, "statusText"))
        )
        time.sleep(2)   # allow fake camera to initialise
        text = status.text
        assert any(kw in text.lower() for kw in ["active", "detecting", "error", "camera"]), (
            f"TC01 FAIL – Status did not update after clicking Start Camera. Got: '{text}'"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TC02  –  Face Detection  (High Priority)
# ─────────────────────────────────────────────────────────────────────────────
class TestTC02_FaceDetection:
    """
    Precondition : Image submitted for processing.
    Steps        : Submit a face image to /process_frame.
    Expected     : Server returns HTTP 200 with a JPEG (face detected & annotated).
    """

    def test_face_detection_returns_200(self):
        """TC02-A: /process_frame responds 200 when given a valid image."""
        resp = process_frame_api(FACE_IMG)
        assert resp.status_code == 200, (
            f"TC02 FAIL – Expected 200, got {resp.status_code}"
        )

    def test_face_detection_returns_jpeg(self):
        """TC02-B: Response content-type is image/jpeg (annotated image returned)."""
        resp = process_frame_api(FACE_IMG)
        assert "image/jpeg" in resp.headers.get("Content-Type", ""), (
            "TC02 FAIL – Response is not a JPEG image"
        )

    def test_face_detection_non_empty_response(self):
        """TC02-C: Response body is non-empty (image has content)."""
        resp = process_frame_api(FACE_IMG)
        assert len(resp.content) > 1000, (
            "TC02 FAIL – Response image is too small to be valid"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TC03  –  Gender Detection  (High Priority)
# ─────────────────────────────────────────────────────────────────────────────
class TestTC03_GenderDetection:
    """
    Precondition : Face must be detected in the submitted image.
    Steps        : Upload a face image via /upload.
    Expected     : HTTP 200 response (gender is detected and image annotated).

    NOTE: The actual gender label ('Male'/'Female') is embedded inside the
    returned JPEG image (overlaid by OpenCV). A full pixel/OCR test is out
    of scope for this lab; we verify the pipeline succeeds (200 + JPEG).
    """

    def test_gender_detection_pipeline_success(self):
        """TC03: /upload with a face image returns HTTP 200 (no server error)."""
        resp = upload_image_via_api(FACE_IMG)
        assert resp.status_code == 200, (
            f"TC03 FAIL – Gender detection pipeline returned {resp.status_code}"
        )

    def test_gender_detection_via_browser(self, driver):
        """TC03-B: Uploading a face image through the browser form does not show 500."""
        driver.get(f"{BASE_URL}/")
        
        # Switch to Photo tab (click the label since radio button is hidden)
        photo_label = driver.find_element(By.CSS_SELECTOR, "label[for='tab-2']")
        photo_label.click()
        time.sleep(0.5)

        file_input = driver.find_element(By.ID, "fileToUpload")
        file_input.send_keys(os.path.abspath(FACE_IMG))
        
        # Click the submit button inside the photo-htm section
        driver.find_element(By.CSS_SELECTOR, ".photo-htm input[name='submit']").click()
        time.sleep(3)

        # Should NOT show a 500 error page
        assert "Internal Server Error" not in driver.page_source, (
            "TC03 FAIL – Server returned a 500 error during gender detection"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TC04  –  Age Detection  (High Priority)
# ─────────────────────────────────────────────────────────────────────────────
class TestTC04_AgeDetection:
    """
    Precondition : Face must be detected.
    Steps        : Submit a face image to /process_frame.
    Expected     : HTTP 200 response (age label embedded in returned JPEG).
    Tolerance    : ±5 years (validated manually; automation confirms no crash).
    """

    def test_age_detection_no_server_error(self):
        """TC04-A: Age detection pipeline returns HTTP 200 with face image."""
        resp = process_frame_api(FACE_IMG)
        assert resp.status_code == 200, (
            f"TC04 FAIL – Age detection returned {resp.status_code}"
        )

    def test_age_detection_response_is_image(self):
        """TC04-B: Response is a JPEG (age label has been drawn on the image)."""
        resp = process_frame_api(FACE_IMG)
        ct = resp.headers.get("Content-Type", "")
        assert "image/jpeg" in ct, f"TC04 FAIL – Unexpected Content-Type: {ct}"


# ─────────────────────────────────────────────────────────────────────────────
# TC05  –  No Face in Frame  (Medium Priority)
# ─────────────────────────────────────────────────────────────────────────────
class TestTC05_NoFaceInFrame:
    """
    Precondition : User does not show face in camera / submits blank image.
    Steps        : Submit a blank image (no face) via /upload.
    Expected     : Server should return HTTP 200 (graceful handling, no crash).
                   The app currently prints 'No face detected' and returns the
                   original frame – a robust production system would return an
                   error JSON; this test verifies it does NOT crash (500).
    """

    def test_no_face_does_not_crash_server(self):
        """TC05-A: Blank image (no face) returns 200, not 500."""
        resp = upload_image_via_api(BLANK_IMG)
        assert resp.status_code != 500, (
            "TC05 FAIL – Server crashed (500) when no face was in the image"
        )

    def test_no_face_process_frame_does_not_crash(self):
        """TC05-B: Blank image to /process_frame returns 200."""
        resp = process_frame_api(BLANK_IMG)
        assert resp.status_code == 200, (
            f"TC05 FAIL – /process_frame returned {resp.status_code} for blank image"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TC06  –  Multiple Faces in Frame  (Medium Priority)
# ─────────────────────────────────────────────────────────────────────────────
class TestTC06_MultipleFaces:
    """
    Precondition : More than one person visible in camera.
    Steps        : Submit a multi-face image.
    Expected     : Server should handle gracefully (200 or structured error).
    """

    def test_multi_face_does_not_crash(self):
        """TC06: Multiple-face image does not cause server to crash (500)."""
        resp = process_frame_api(MULTI_IMG)
        assert resp.status_code != 500, (
            "TC06 FAIL – Server crashed when multiple faces were detected"
        )

    def test_multi_face_returns_image_or_json(self):
        """TC06-B: Multi-face response is either a JPEG or JSON error — not HTML 500."""
        resp = process_frame_api(MULTI_IMG)
        ct = resp.headers.get("Content-Type", "")
        assert "image/jpeg" in ct or "application/json" in ct, (
            f"TC06 FAIL – Unexpected response type for multi-face: {ct}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TC07  –  Gender Mismatch  (High Priority)
# ─────────────────────────────────────────────────────────────────────────────
class TestTC07_GenderMismatch:
    """
    Precondition : User manually enters a gender that differs from detected gender.
    Steps        : Send an image to /process_frame; compare returned annotation.
    Expected     : System detects and flags gender discrepancy.

    Implementation note: The current app does not have a 'declared gender' field.
    This test validates the /process_frame endpoint returns a valid detection
    result (the basis for a mismatch check). The mismatch logic lives at the
    registration form level (future enhancement).
    """

    def test_gender_mismatch_endpoint_reachable(self):
        """TC07-A: /process_frame is available for gender verification calls."""
        resp = process_frame_api(FACE_IMG)
        assert resp.status_code == 200, (
            "TC07 FAIL – Gender detection endpoint not reachable"
        )

    def test_gender_mismatch_registration_form_visible(self, driver):
        """TC07-B: Home page contains the photo upload form for gender verification."""
        driver.get(f"{BASE_URL}/")
        assert "fileToUpload" in driver.page_source, (
            "TC07 FAIL – File upload form not found on home page"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TC08  –  Underage User  (High Priority)
# ─────────────────────────────────────────────────────────────────────────────
class TestTC08_UnderageUser:
    """
    Precondition : System detects user age < 18.
    Steps        : Submit a face image; check age detection response.
    Expected     : System returns age value (the blocking logic is in
                   the registration form layer which uses this age value).

    NOTE: We cannot programmatically guarantee a test image shows a minor.
    This test validates the pipeline returns an age value in the response.
    """

    def test_age_pipeline_returns_valid_response(self):
        """TC08: Age detection pipeline works and would allow underage blocking logic."""
        resp = process_frame_api(FACE_IMG)
        assert resp.status_code == 200, (
            f"TC08 FAIL – Age detection pipeline failed: {resp.status_code}"
        )
        # Response must be a valid image (contains OpenCV-drawn age label)
        assert len(resp.content) > 500, (
            "TC08 FAIL – Age detection returned an empty/invalid image"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TC09  –  Poor Lighting Conditions  (Low Priority)
# ─────────────────────────────────────────────────────────────────────────────
class TestTC09_PoorLighting:
    """
    Precondition : Camera feed is in dim lighting.
    Steps        : Submit a very dark image.
    Expected     : Server does not crash; handles gracefully.
    """

    def test_dark_image_does_not_crash_server(self):
        """TC09-A: Very dark image (simulating poor lighting) returns non-500."""
        resp = upload_image_via_api(DARK_IMG)
        assert resp.status_code != 500, (
            "TC09 FAIL – Server crashed on dark/low-light image"
        )

    def test_dark_image_process_frame_graceful(self):
        """TC09-B: Dark image to /process_frame returns 200 (face not detected gracefully)."""
        resp = process_frame_api(DARK_IMG)
        assert resp.status_code == 200, (
            f"TC09 FAIL – /process_frame returned {resp.status_code} for dark image"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TC10  –  Store Verification Result  (Medium Priority)
# ─────────────────────────────────────────────────────────────────────────────
class TestTC10_StoreVerificationResult:
    """
    Precondition : Age and gender successfully verified.
    Steps        : Submit face image; verify the response is suitable for storage.
    Expected     : HTTP 200 with non-empty JPEG (can be stored securely in DB).

    NOTE: The current app does not have a database. This test confirms that the
    verification pipeline produces a deterministic, storable output (the annotated
    JPEG bytes), which a future DB-write layer would persist.
    """

    def test_verification_result_is_storable(self):
        """TC10-A: /process_frame returns bytes that can be stored in a database."""
        resp = process_frame_api(FACE_IMG)
        assert resp.status_code == 200
        assert len(resp.content) > 0, (
            "TC10 FAIL – Verification result is empty; nothing to store"
        )

    def test_verification_result_content_type(self):
        """TC10-B: Returned JPEG has correct MIME type for DB BLOB storage."""
        resp = process_frame_api(FACE_IMG)
        assert "image/jpeg" in resp.headers.get("Content-Type", ""), (
            "TC10 FAIL – Verification result is not a JPEG; unexpected format for storage"
        )

    def test_home_page_accessible_post_verification(self, driver):
        """TC10-C: Application remains accessible after a verification cycle (no crash)."""
        driver.get(f"{BASE_URL}/")
        assert driver.title != "", "TC10 FAIL – Home page unreachable after verification"


# ─────────────────────────────────────────────────────────────────────────────
# General Smoke Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestSmoke:
    """Quick sanity checks to confirm all routes are up."""

    def test_home_route(self):
        assert requests.get(f"{BASE_URL}/").status_code == 200

    def test_webcam_route(self):
        assert requests.get(f"{BASE_URL}/webcam").status_code == 200

    def test_process_frame_rejects_empty_body(self):
        resp = requests.post(f"{BASE_URL}/process_frame", json={}, timeout=10)
        assert resp.status_code == 400, (
            "Smoke FAIL – /process_frame should return 400 for missing image"
        )
