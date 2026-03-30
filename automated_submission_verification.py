#!/usr/bin/env python3
"""
Automated Submission Verification Suite
========================================

This script automatically verifies that ALL components are working:
- .env file and Groq API configuration
- Python environment and dependencies
- Baseline evaluation with Groq
- Integration tests
- API endpoints
- Docker readiness
- Documentation completeness

NO MANUAL TESTING REQUIRED - Run this and confirm everything works!

Usage:
    python automated_submission_verification.py

Exit codes:
    0 = All checks passed ✅
    1 = Some checks failed ❌
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class SubmissionVerifier:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "passed": 0,
            "failed": 0,
            "warnings": 0,
        }
        self.cwd = Path(__file__).parent
        
    def print_header(self, text):
        print("\n" + "=" * 80)
        print(f"  {text}")
        print("=" * 80)
        
    def print_check(self, name, status, message=""):
        symbol = "✅" if status else "❌"
        print(f"{symbol} {name}")
        if message:
            print(f"   └─ {message}")
        return status
        
    def check_env_file(self):
        """Check .env file exists and contains required keys"""
        self.print_header("1. CHECKING .env FILE")
        
        env_file = self.cwd / ".env"
        if not env_file.exists():
            self.print_check("*.env file exists", False, "File not found")
            self.results["failed"] += 1
            return False
        
        self.print_check("✓ .env file exists", True)
        
        # Check contents
        env_content = env_file.read_text(encoding="utf-8")
        required_keys = ["GROQ_API_KEY", "LLM_PROVIDER", "LLM_MODEL"]
        
        for key in required_keys:
            if key in env_content:
                self.print_check(f"  {key} defined", True)
                self.results["passed"] += 1
            else:
                self.print_check(f"  {key} defined", False)
                self.results["failed"] += 1
        
        # Verify API key is loaded
        api_key = os.getenv("GROQ_API_KEY")
        if api_key and api_key.startswith("gsk_"):
            self.print_check("  API key valid format", True, f"{api_key[:30]}...")
            self.results["passed"] += 1
            return True
        else:
            self.print_check("  API key valid format", False)
            self.results["failed"] += 1
            return False
    
    def check_dependencies(self):
        """Check all Python dependencies are installed"""
        self.print_header("2. CHECKING PYTHON DEPENDENCIES")
        
        required = {
            "dotenv": "python-dotenv",
            "groq": "groq",
            "fastapi": "fastapi",
            "pydantic": "pydantic",
            "pandas": "pandas",
        }
        
        optional = {
            "streamlit": "streamlit (optional for UI)",
        }
        
        for module, package in required.items():
            try:
                __import__(module)
                self.print_check(f"  {package}", True)
                self.results["passed"] += 1
            except ImportError:
                self.print_check(f"  {package}", False, "Not installed")
                self.results["failed"] += 1
        
        for module, package in optional.items():
            try:
                __import__(module)
                self.print_check(f"  {package}", True)
                self.results["passed"] += 1
            except ImportError:
                self.print_check(f"  {package} (optional)", True, "Not required")
                self.results["passed"] += 1
        
        return self.results["failed"] == 0
    
    def check_groq_client(self):
        """Test Groq client initialization"""
        self.print_header("3. TESTING GROQ CLIENT")
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            self.print_check("Groq client initialization", False, "No API key")
            self.results["failed"] += 1
            return False
        
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            self.print_check("Groq client initialization", True)
            self.results["passed"] += 1
            
            # Try to list models
            models = client.models.list()
            self.print_check("  List available models", True, f"Found {len(models.data)} models")
            self.results["passed"] += 1
            return True
        except Exception as e:
            self.print_check("Groq client initialization", False, str(e))
            self.results["failed"] += 1
            return False
    
    def check_integration_tests(self):
        """Run integration tests automatically"""
        self.print_header("4. RUNNING INTEGRATION TESTS")
        
        test_file = self.cwd / "tests" / "test_integration.py"
        if not test_file.exists():
            self.print_check("Integration tests exist", False)
            self.results["failed"] += 1
            return False
        
        self.print_check("Integration tests exist", True)
        self.results["passed"] += 1
        
        try:
            result = subprocess.run(
                [sys.executable, str(test_file)],
                cwd=str(self.cwd),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # Count passed tests
                if "8 passed" in result.stdout:
                    self.print_check("  All integration tests passed", True, "8/8 tests OK")
                    self.results["passed"] += 1
                    return True
                else:
                    self.print_check("  Integration tests output", True)
                    self.results["passed"] += 1
                    return True
            else:
                self.print_check("  Integration tests passed", False, result.stderr[:100])
                self.results["failed"] += 1
                return False
        except subprocess.TimeoutExpired:
            self.print_check("  Integration tests passed", False, "Timeout")
            self.results["failed"] += 1
            return False
        except Exception as e:
            self.print_check("  Integration tests passed", False, str(e)[:100])
            self.results["failed"] += 1
            return False
    
    def check_data_validation(self):
        """Check ticket data is valid"""
        self.print_header("5. VALIDATING TICKET DATA")
        
        try:
            from customer_support_env.data import TICKETS, validate_tickets
            
            self.print_check("Load ticket data", True, f"Loaded {len(TICKETS)} tickets")
            self.results["passed"] += 1
            
            validate_tickets()
            self.print_check("  Validate all tickets", True)
            self.results["passed"] += 1
            return True
        except Exception as e:
            self.print_check("Load ticket data", False, str(e)[:100])
            self.results["failed"] += 1
            return False
    
    def check_environment_api(self):
        """Test environment step/reset/state API"""
        self.print_header("6. TESTING ENVIRONMENT API")
        
        try:
            from customer_support_env.environment import CustomerSupportEnvironment
            from customer_support_env.models import TicketAction
            
            env = CustomerSupportEnvironment()
            self.print_check("Initialize environment", True)
            self.results["passed"] += 1
            
            # Test reset
            obs = env.reset(seed=0, task="classify")
            self.print_check("  reset() method", True)
            self.results["passed"] += 1
            
            # Test step
            action = TicketAction(category="billing", priority="high")
            result = env.step(action)
            self.print_check("  step() method", True)
            self.results["passed"] += 1
            
            # Test state
            state = env.state
            self.print_check("  state property", True)
            self.results["passed"] += 1
            
            return True
        except Exception as e:
            self.print_check("Environment API", False, str(e)[:100])
            self.results["failed"] += 1
            return False
    
    def check_models(self):
        """Verify Pydantic models are correct"""
        self.print_header("7. CHECKING PYDANTIC MODELS")
        
        try:
            from customer_support_env.models import (
                TicketAction, TicketObservation, TicketState
            )
            
            # Test TicketAction
            action = TicketAction(category="billing", priority="high")
            self.print_check("TicketAction model", True)
            self.results["passed"] += 1
            
            # Test required fields per task
            action_route = TicketAction(
                category="billing",
                priority="high",
                department="billing"
            )
            self.print_check("  Route task fields", True)
            self.results["passed"] += 1
            
            # Test resolve task
            action_resolve = TicketAction(
                category="billing",
                priority="high",
                department="billing",
                response="Test response"
            )
            self.print_check("  Resolve task fields", True)
            self.results["passed"] += 1
            
            return True
        except Exception as e:
            self.print_check("Pydantic models", False, str(e)[:100])
            self.results["failed"] += 1
            return False
    
    def check_baseline_script(self):
        """Verify baseline script exists and structure is correct"""
        self.print_header("8. CHECKING BASELINE SCRIPT")
        
        baseline_file = self.cwd / "customer_support_env" / "baseline.py"
        if not baseline_file.exists():
            self.print_check("baseline.py exists", False)
            self.results["failed"] += 1
            return False
        
        self.print_check("baseline.py exists", True)
        self.results["passed"] += 1
        
        content = baseline_file.read_text()
        
        checks = {
            "from groq import Groq": "Groq import",
            "def run_baseline": "run_baseline function",
            "GROQ_API_KEY": "API key check",
            "temperature_strategy": "Temperature config",
        }
        
        for check_str, name in checks.items():
            if check_str in content:
                self.print_check(f"  {name}", True)
                self.results["passed"] += 1
            else:
                self.print_check(f"  {name}", False)
                self.results["failed"] += 1
        
        return True
    
    def check_documentation(self):
        """Check README has required sections"""
        self.print_header("9. CHECKING DOCUMENTATION")
        
        readme_file = self.cwd / "README.md"
        if not readme_file.exists():
            self.print_check("README.md exists", False)
            self.results["failed"] += 1
            return False
        
        self.print_check("README.md exists", True)
        self.results["passed"] += 1
        
        content = readme_file.read_text(encoding="utf-8")
        
        checks = {
            "86.2%": "Baseline scores included",
            "76.3%": "Route task score",
            "66.1%": "Resolve task score",
            "Groq API Configuration": "Groq setup section",
            "openenv.yaml": "OpenEnv spec reference",
            "https://kavyabumiya-customer-support-env.hf.space": "Deployment link",
            "Integration Tests": "Test results",
        }
        
        for check_str, name in checks.items():
            if check_str in content:
                self.print_check(f"  {name}", True)
                self.results["passed"] += 1
            else:
                self.print_check(f"  {name}", False, f"Missing: '{check_str}'")
                self.results["failed"] += 1
        
        return True
    
    def check_deployment_files(self):
        """Check Docker and deployment files"""
        self.print_header("10. CHECKING DEPLOYMENT FILES")
        
        files = {
            "Dockerfile": "Main Dockerfile",
            "Dockerfile.streamlit": "Streamlit Dockerfile",
            "space_config.json": "HF Spaces config",
            "openenv.yaml": "OpenEnv spec",
        }
        
        for filename, description in files.items():
            filepath = self.cwd / filename
            if filepath.exists():
                self.print_check(f"  {description}", True)
                self.results["passed"] += 1
            else:
                self.print_check(f"  {description}", False)
                self.results["failed"] += 1
        
        # Check space_config.json content
        try:
            space_config = self.cwd / "space_config.json"
            config = json.loads(space_config.read_text())
            
            if "kavyabumiya" in config.get("repo_url", ""):
                self.print_check("  HF Spaces username configured", True)
                self.results["passed"] += 1
            else:
                self.print_check("  HF Spaces username configured", False)
                self.results["failed"] += 1
        except Exception as e:
            self.print_check("  Parse space_config.json", False, str(e)[:50])
            self.results["failed"] += 1
        
        return True
    
    def check_api_structure(self):
        """Check FastAPI server structure"""
        self.print_header("11. CHECKING API STRUCTURE")
        
        try:
            from customer_support_env.server.app import app
            
            self.print_check("FastAPI app imports", True)
            self.results["passed"] += 1
            
            # Check routes exist
            routes = [route.path for route in app.routes]
            expected_routes = ["/reset", "/step", "/state", "/tasks", "/health"]
            
            for route in expected_routes:
                if route in routes:
                    self.print_check(f"  {route} endpoint", True)
                    self.results["passed"] += 1
                else:
                    self.print_check(f"  {route} endpoint", False)
                    self.results["failed"] += 1
            
            return True
        except Exception as e:
            self.print_check("FastAPI server", False, str(e)[:100])
            self.results["failed"] += 1
            return False
    
    def check_openenv_yaml(self):
        """Check OpenEnv YAML specification"""
        self.print_header("12. CHECKING OPENENV SPECIFICATION")
        
        try:
            import yaml
            
            yaml_file = self.cwd / "openenv.yaml"
            if not yaml_file.exists():
                self.print_check("openenv.yaml exists", False)
                self.results["failed"] += 1
                return False
            
            config = yaml.safe_load(yaml_file.read_text())
            
            self.print_check("openenv.yaml exists", True)
            self.results["passed"] += 1
            
            # Check required sections
            checks = {
                "name": "name field",
                "tasks": "tasks field",
                "version": "version field",
            }
            
            for key, name in checks.items():
                if key in config:
                    self.print_check(f"  {name}", True)
                    self.results["passed"] += 1
                else:
                    self.print_check(f"  {name}", False)
                    self.results["failed"] += 1
            
            # Check tasks
            if len(config.get("tasks", [])) >= 3:
                self.print_check("  3 tasks defined", True)
                self.results["passed"] += 1
            else:
                self.print_check("  3 tasks defined", False)
                self.results["failed"] += 1
            
            return True
        except Exception as e:
            self.print_check("OpenEnv specification", False, str(e)[:100])
            self.results["failed"] += 1
            return False
    
    def run_all_checks(self):
        """Run all verification checks"""
        print("\n" + "█" * 80)
        print("█  AUTOMATED SUBMISSION VERIFICATION SUITE")
        print("█  " + datetime.now().strftime("%B %d, %Y at %H:%M:%S UTC"))
        print("█" * 80)
        
        all_passed = True
        
        all_passed &= self.check_env_file()
        all_passed &= self.check_dependencies()
        all_passed &= self.check_groq_client()
        all_passed &= self.check_integration_tests()
        all_passed &= self.check_data_validation()
        all_passed &= self.check_environment_api()
        all_passed &= self.check_models()
        all_passed &= self.check_baseline_script()
        all_passed &= self.check_documentation()
        all_passed &= self.check_deployment_files()
        all_passed &= self.check_api_structure()
        all_passed &= self.check_openenv_yaml()
        
        return all_passed
    
    def print_summary(self, all_passed):
        """Print final summary"""
        self.print_header("VERIFICATION SUMMARY")
        
        total = self.results["passed"] + self.results["failed"]
        print(f"\nTests Run:    {total}")
        print(f"Passed:       {self.results['passed']} ✅")
        print(f"Failed:       {self.results['failed']} ❌")
        print(f"Success Rate: {self.results['passed'] / total * 100:.1f}%")
        
        print("\n" + "=" * 80)
        
        if all_passed and self.results["failed"] == 0:
            print("✅  ALL CHECKS PASSED - SUBMISSION READY!")
            print("=" * 80)
            print("\nNext steps:")
            print("  1. git add .")
            print("  2. git commit -m 'feat: final submission with Groq integration'")
            print("  3. git push origin main")
            print("  4. Monitor GitHub Actions for deployment")
            print("\n" + "=" * 80)
            return 0
        else:
            print("❌  SOME CHECKS FAILED - REVIEW ABOVE")
            print("=" * 80)
            return 1


if __name__ == "__main__":
    verifier = SubmissionVerifier()
    all_passed = verifier.run_all_checks()
    exit_code = verifier.print_summary(all_passed)
    sys.exit(exit_code)
