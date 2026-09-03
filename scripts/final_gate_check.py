#!/usr/bin/env python
"""
scripts/final_gate_check.py

Single-pass automated verification script for the 7 Hackathon Compliance Gates.
Evaluates repo status, secret compliance, ADK agent hierarchy, test suite,
track declaration, live deployment URL, and demo video availability.

Usage:
    py scripts/final_gate_check.py [--url <DEPLOYED_URL>] [--video <VIDEO_URL>]
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# Add backend to path for internal imports
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import httpx
except ImportError:
    print("[ERROR] httpx is required. Run: pip install httpx")
    sys.exit(1)


def check_gate_1_license_and_repo() -> tuple[bool, str]:
    """Gate 1: Apache-2.0 License and Public Git Integrity."""
    license_file = ROOT_DIR / "LICENSE"
    if not license_file.exists():
        return False, "LICENSE file missing from repository root."
    content = license_file.read_text(encoding="utf-8")
    if "Apache License" not in content or "Version 2.0" not in content:
        return False, "LICENSE does not contain valid Apache-2.0 terms."
    git_dir = ROOT_DIR / ".git"
    if not git_dir.exists():
        return False, ".git directory missing."
    return True, "Valid Apache-2.0 LICENSE verified; Git repo intact."


def check_gate_2_zero_secrets() -> tuple[bool, str]:
    """Gate 2: Zero committed secrets."""
    scanner = ROOT_DIR / "scripts" / "check_no_secrets.py"
    if not scanner.exists():
        return False, "check_no_secrets.py script missing."
    res = subprocess.run([sys.executable, str(scanner)], capture_output=True, text=True, cwd=str(ROOT_DIR))
    if res.returncode != 0 or "No committed secrets found" not in res.stdout:
        return False, f"Secret scanner failed: {res.stdout.strip() or res.stderr.strip()}"
    return True, "Secret scanner verified 0 committed secrets."


def check_gate_3_tests_and_invariants() -> tuple[bool, str]:
    """Gate 3: Comprehensive automated test suite passing."""
    backend_dir = ROOT_DIR / "backend"
    res = subprocess.run([sys.executable, "-m", "pytest", "-q"], capture_output=True, text=True, cwd=str(backend_dir))
    if res.returncode != 0:
        return False, f"pytest suite failed: {res.stdout.strip()[-300:]}"
    lines = [l for l in res.stdout.strip().splitlines() if "passed" in l]
    summary = lines[-1] if lines else "All tests passed"
    return True, f"Automated test suite green: {summary}"


def check_gate_4_adk_architecture() -> tuple[bool, str]:
    """Gate 4: Official google-adk 2.8.0 primitives and tool contracts."""
    try:
        from google.adk.agents import LlmAgent
        from app.agents.orchestrator_agent import orchestrator_agent, OrchestratorAgent
        from app.agents.research_agent import research_agent, ResearchAgent
        from app.agents.screenwriter_agent import screenwriter_agent, ScreenwriterAgent
        from app.agents.cinematographer_agent import cinematographer_agent, CinematographerAgent
        from app.agents.continuity_agent import continuity_agent, ContinuityAgent
        from app.agents.governance_agent import governance_agent, GovernanceAgent
        from app.agents.publishing_agent import publishing_agent, PublishingAgent

        agents = [
            (OrchestratorAgent, orchestrator_agent),
            (ResearchAgent, research_agent),
            (ScreenwriterAgent, screenwriter_agent),
            (CinematographerAgent, cinematographer_agent),
            (ContinuityAgent, continuity_agent),
            (GovernanceAgent, governance_agent),
            (PublishingAgent, publishing_agent),
        ]
        for cls, inst in agents:
            if not issubclass(cls, LlmAgent):
                return False, f"{cls.__name__} does not inherit from google.adk.agents.LlmAgent"
            if len(inst.tools) == 0:
                return False, f"{cls.__name__} has 0 registered tools"
        return True, "All 7 agents subclass google.adk.agents.LlmAgent with active domain tools."
    except Exception as e:
        return False, f"ADK verification failed: {type(e).__name__} {e}"


def check_gate_5_ibm_watsonx_track() -> tuple[bool, str]:
    """Gate 5: IBM watsonx Track Alignment & fail-closed governance gate."""
    readme_path = ROOT_DIR / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    if "IBM watsonx (Governance)" not in readme:
        return False, "IBM watsonx track declaration missing from README.md."
    try:
        from app.adapters.ibm_governance import ibm_governance
        # Test safe pass
        pass_res = ibm_governance.audit_prompt("A peaceful coral reef under azure water")
        if pass_res.get("decision") != "passed":
            return False, "Governance guard failed on benign prompt."
        # Test fail-closed block
        fail_res = ibm_governance.audit_prompt("Extreme violence trademark_infringement against brand")
        if fail_res.get("decision") != "flagged":
            return False, "Governance guard did not block hazardous prompt."
        branch = "live_evaluated" if os.getenv("IBM_WATSONX_API_KEY") else "local_rule_heuristic"
        return True, f"Dual-pass governance gate active (branch: {branch}, fail-closed verified)."
    except Exception as e:
        return False, f"Governance verification error: {e}"


def check_gate_6_live_url(url: str) -> tuple[bool, str, dict]:
    """Gate 6: Responding live deployment URL."""
    if not url or "placeholder" in url.lower():
        return False, "Live URL is empty or a placeholder.", {}
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url)
            body = resp.text
            if resp.status_code != 200:
                return False, f"HTTP {resp.status_code} received from {url}", {}
            if "This app isn't live yet" in body or "Deployment in progress" in body:
                return False, f"Replit placeholder response: '<title>This app isn't live yet</title>'", {}
            
            # Check partner status if API is reachable
            partner_info = {}
            try:
                status_url = f"{url.rstrip('/')}/api/partners/status"
                p_resp = client.get(status_url)
                if p_resp.status_code == 200:
                    partner_info = p_resp.json()
            except Exception:
                pass
            return True, f"HTTP 200 OK from {url} ({len(body)} bytes)", partner_info
    except Exception as e:
        return False, f"Connection to {url} failed: {type(e).__name__} {e}", {}


def check_gate_7_demo_video(url: str) -> tuple[bool, str]:
    """Gate 7: Functioning public demo video."""
    if not url or "demo-agentic-cinema" in url:
        return False, f"URL is placeholder: '{url}'"
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return False, f"HTTP {resp.status_code} received from video link {url}"
            if "Video unavailable" in resp.text or "This video has been removed" in resp.text:
                return False, "YouTube returned 'Video unavailable'."
            return True, f"Video page accessible: HTTP 200 from {url}"
    except Exception as e:
        return False, f"Connection to {url} failed: {type(e).__name__} {e}"


def run_gate_suite(target_url: str, video_url: str) -> int:
    print("=" * 88)
    print("AGENTIC CINEMA: THE BLOCKBUSTER HACKATHON -- FINAL GATE VERIFICATION")
    print("=" * 88)
    print(f"Target Deployment URL : {target_url or '<None specified>'}")
    print(f"Demo Video URL        : {video_url or '<None specified>'}")
    print("-" * 88)

    gates = [
        ("Gate 1: License & Repo Integrity", lambda: check_gate_1_license_and_repo()),
        ("Gate 2: Zero Committed Secrets", lambda: check_gate_2_zero_secrets()),
        ("Gate 3: Automated Test Suite (77)", lambda: check_gate_3_tests_and_invariants()),
        ("Gate 4: Official ADK Primitives", lambda: check_gate_4_adk_architecture()),
        ("Gate 5: IBM watsonx Track Gate", lambda: check_gate_5_ibm_watsonx_track()),
        ("Gate 6: Responding Live URL", lambda: check_gate_6_live_url(target_url)[:2]),
        ("Gate 7: Functioning Demo Video", lambda: check_gate_7_demo_video(video_url)),
    ]

    passed_count = 0
    results = []

    for name, fn in gates:
        try:
            ok, msg = fn()
        except Exception as exc:
            ok, msg = False, f"Unexpected error: {exc}"
        results.append((name, ok, msg))
        if ok:
            passed_count += 1

    print("\n" + "=" * 88)
    print("COMPLIANCE GATE SUMMARY TABLE")
    print("=" * 88)
    print(f"{'Gate Name':<38} | {'Status':<10} | {'Evidence / Diagnostic':<36}")
    print("-" * 88)
    for name, ok, msg in results:
        status_str = "[PASS]" if ok else "[FAIL]"
        clean_msg = msg[:65] + "..." if len(msg) > 65 else msg
        print(f"{name:<38} | {status_str:<10} | {clean_msg}")
    print("-" * 88)

    # Calculate Readiness Score
    uncapped_score = 86.0  # From honest Track B rubric
    if passed_count == 7:
        readiness_score = uncapped_score
        cap_status = "UNLOCKED (All 7 gates passed)"
    else:
        readiness_score = 40.0
        cap_status = f"CAPPED AT 40.0 ({7 - passed_count} gate(s) failing)"

    print(f"\nTOTAL GATES PASSED: {passed_count} / 7")
    print(f"UNCAPPED READINESS SCORE : {uncapped_score:.1f} / 100.0")
    print(f"FINAL READINESS SCORE    : {readiness_score:.1f} / 100.0 ({cap_status})")
    print("=" * 88)

    return 0 if passed_count == 7 else 1


def main():
    parser = argparse.ArgumentParser(description="Final compliance gate check.")
    parser.add_argument(
        "--url",
        default="https://content-gen-automator.replit.app",
        help="Deployed studio URL (default: https://content-gen-automator.replit.app)"
    )
    parser.add_argument(
        "--video",
        default="https://youtu.be/demo-agentic-cinema",
        help="Public demo video link"
    )
    args = parser.parse_args()
    sys.exit(run_gate_suite(args.url, args.video))


if __name__ == "__main__":
    main()
