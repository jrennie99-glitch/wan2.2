#!/usr/bin/env python3
"""
Backend API Testing for WAN 2.2 Gateway Application
Tests all API endpoints and job simulation functionality
"""

import requests
import sys
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional

class WAN22GatewayTester:
    def __init__(self, base_url: str = "https://e2c1c67c-bb0b-4900-8b28-63204cf57835.preview.emergentagent.com"):
        self.base_url = base_url.rstrip('/')
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED")
        else:
            print(f"❌ {name}: FAILED - {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "response_data": response_data
        })

    def test_get_root(self):
        """Test GET / returns 200 with HTML page"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            success = response.status_code == 200 and "html" in response.headers.get("content-type", "").lower()
            details = f"Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'N/A')}"
            
            # Check for DreamAI-style UI elements
            if success and response.text:
                has_dream_studio = "Dream Studio" in response.text
                has_wan_22 = "WAN 2.2" in response.text
                if not (has_dream_studio and has_wan_22):
                    success = False
                    details += f" | Missing UI elements: Dream Studio={has_dream_studio}, WAN 2.2={has_wan_22}"
                else:
                    details += " | UI elements found: Dream Studio ✓, WAN 2.2 ✓"
            
            self.log_test("GET / (HTML page with UI elements)", success, details)
            return success
        except Exception as e:
            self.log_test("GET / (HTML page with UI elements)", False, f"Exception: {str(e)}")
            return False

    def test_head_root(self):
        """Test HEAD / returns 200 (Render health check)"""
        try:
            response = requests.head(f"{self.base_url}/", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            self.log_test("HEAD / (Render health check)", success, details)
            return success
        except Exception as e:
            self.log_test("HEAD / (Render health check)", False, f"Exception: {str(e)}")
            return False

    def test_health_endpoint(self):
        """Test GET /health returns {ok: true}"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            success = response.status_code == 200
            
            if success:
                try:
                    data = response.json()
                    has_ok = data.get("ok") is True
                    if not has_ok:
                        success = False
                        details = f"Status: {response.status_code}, Missing 'ok: true' in response: {data}"
                    else:
                        details = f"Status: {response.status_code}, Response: {data}"
                except json.JSONDecodeError:
                    success = False
                    details = f"Status: {response.status_code}, Invalid JSON response"
            else:
                details = f"Status: {response.status_code}"
            
            self.log_test("GET /health", success, details, response.json() if success else None)
            return success
        except Exception as e:
            self.log_test("GET /health", False, f"Exception: {str(e)}")
            return False

    def test_create_job(self) -> Optional[str]:
        """Test POST /api/jobs creates a job and returns {ok, job_id, status: queued}"""
        try:
            payload = {
                "prompt": "A majestic eagle soaring through golden sunset clouds, cinematic 4K",
                "negative_prompt": "blurry, low quality",
                "seed": -1,
                "steps": 30,
                "cfg_scale": 7.5,
                "duration_seconds": 4.0,
                "fps": 24,
                "width": 512,
                "height": 512
            }
            
            response = requests.post(
                f"{self.base_url}/api/jobs",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            success = response.status_code == 200
            job_id = None
            
            if success:
                try:
                    data = response.json()
                    has_ok = data.get("ok") is True
                    job_id = data.get("job_id")
                    status = data.get("status")
                    
                    if not (has_ok and job_id and status == "queued"):
                        success = False
                        details = f"Status: {response.status_code}, Invalid response format: {data}"
                    else:
                        details = f"Status: {response.status_code}, Job created: {job_id}, Status: {status}"
                except json.JSONDecodeError:
                    success = False
                    details = f"Status: {response.status_code}, Invalid JSON response"
            else:
                details = f"Status: {response.status_code}"
            
            self.log_test("POST /api/jobs (create job)", success, details, response.json() if success else None)
            return job_id if success else None
        except Exception as e:
            self.log_test("POST /api/jobs (create job)", False, f"Exception: {str(e)}")
            return None

    def test_get_job_status(self, job_id: str):
        """Test GET /api/jobs/{job_id} returns job status with progress"""
        try:
            response = requests.get(f"{self.base_url}/api/jobs/{job_id}", timeout=10)
            success = response.status_code == 200
            
            if success:
                try:
                    data = response.json()
                    required_fields = ["job_id", "status", "progress"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if missing_fields:
                        success = False
                        details = f"Status: {response.status_code}, Missing fields: {missing_fields}"
                    else:
                        details = f"Status: {response.status_code}, Job: {data.get('job_id')}, Status: {data.get('status')}, Progress: {data.get('progress')}%"
                except json.JSONDecodeError:
                    success = False
                    details = f"Status: {response.status_code}, Invalid JSON response"
            else:
                details = f"Status: {response.status_code}"
            
            self.log_test("GET /api/jobs/{job_id} (job status)", success, details, response.json() if success else None)
            return success, response.json() if success else None
        except Exception as e:
            self.log_test("GET /api/jobs/{job_id} (job status)", False, f"Exception: {str(e)}")
            return False, None

    def test_job_completion_simulation(self, job_id: str):
        """Test that job completes after 5-10 seconds in simulation mode"""
        print(f"\n🔄 Testing job completion simulation for job: {job_id}")
        start_time = time.time()
        max_wait = 15  # Allow up to 15 seconds for completion
        poll_interval = 2
        
        completed = False
        final_status = None
        completion_time = None
        
        while time.time() - start_time < max_wait:
            success, job_data = self.test_get_job_status(job_id)
            if not success:
                break
                
            status = job_data.get("status")
            progress = job_data.get("progress", 0)
            
            print(f"  ⏱️  {time.time() - start_time:.1f}s - Status: {status}, Progress: {progress}%")
            
            if status == "completed":
                completed = True
                completion_time = time.time() - start_time
                final_status = job_data
                break
            elif status == "failed":
                final_status = job_data
                break
                
            time.sleep(poll_interval)
        
        # Evaluate simulation test
        if completed and 5 <= completion_time <= 12:  # Allow some buffer
            details = f"Job completed in {completion_time:.1f}s (expected 5-10s)"
            self.log_test("Job completion simulation (5-10 seconds)", True, details, final_status)
        elif completed:
            details = f"Job completed in {completion_time:.1f}s (outside expected 5-10s range)"
            self.log_test("Job completion simulation (5-10 seconds)", False, details, final_status)
        else:
            details = f"Job did not complete within {max_wait}s. Final status: {final_status.get('status') if final_status else 'unknown'}"
            self.log_test("Job completion simulation (5-10 seconds)", False, details, final_status)
        
        return completed, final_status

    def test_page_routes(self):
        """Test that gallery, history, and settings pages work"""
        pages = [
            ("/gallery", "Gallery page"),
            ("/history", "History page"), 
            ("/settings", "Settings page")
        ]
        
        for path, name in pages:
            try:
                response = requests.get(f"{self.base_url}{path}", timeout=10)
                success = response.status_code == 200 and "html" in response.headers.get("content-type", "").lower()
                details = f"Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'N/A')}"
                self.log_test(f"GET {path} ({name})", success, details)
            except Exception as e:
                self.log_test(f"GET {path} ({name})", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting WAN 2.2 Gateway Backend Tests")
        print(f"📍 Base URL: {self.base_url}")
        print("=" * 60)
        
        # Basic endpoint tests
        self.test_get_root()
        self.test_head_root()
        self.test_health_endpoint()
        
        # Page route tests
        self.test_page_routes()
        
        # Job API tests
        job_id = self.test_create_job()
        if job_id:
            # Test job status retrieval
            self.test_get_job_status(job_id)
            
            # Test job completion simulation
            self.test_job_completion_simulation(job_id)
        else:
            print("❌ Skipping job completion tests due to job creation failure")
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return 1

def main():
    """Main test runner"""
    tester = WAN22GatewayTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())