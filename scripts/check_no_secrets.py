#!/usr/bin/env python3
"""
CI Secret Scanner for ContentGenAutomator.
Scans codebase to prevent committing real API keys or sensitive secrets into source control.
"""

import re
import sys
from pathlib import Path

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

# High-risk patterns
SECRET_PATTERNS = [
    (r"AIzaSy[0-9A-Za-z_-]{33}", "Google API Key"),
    (r"sk-[a-zA-Z0-9]{32,}", "OpenAI / ElevenLabs Key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "Private Cryptographic Key"),
    (r"xox[baprs]-[0-9a-zA-Z]{10,}", "Slack Token"),
    (r"(?i)api[_-]?key\s*=\s*['\"][0-9a-zA-Z-_]{24,}['\"]", "Generic Assigned API Key"),
]

IGNORED_PATHS = [
    ".git",
    ".pytest_cache",
    "node_modules",
    ".next",
    "__pycache__",
    "check_no_secrets.py",
    "test_",
    "mock",
    ".gemini",
]

def scan_file(filepath: Path) -> list:
    findings = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    for line_num, line in enumerate(content.splitlines(), start=1):
        # Skip comment headers or placeholders
        if "your_" in line.lower() or "example" in line.lower() or "test_secret" in line.lower():
            continue
        for pattern, desc in SECRET_PATTERNS:
            if re.search(pattern, line):
                findings.append((line_num, desc, line.strip()[:60]))
    return findings

def main():
    root = Path(__file__).resolve().parents[1]
    violations = 0

    print(f"[SCAN] Scanning repository at {root} for hardcoded secrets...")
    for path in root.rglob("*"):
        if path.is_file():
            if any(ignored in str(path) for ignored in IGNORED_PATHS):
                continue
            findings = scan_file(path)
            for line_num, desc, snippet in findings:
                print(f"[POTENTIAL SECRET] {path.relative_to(root)}:{line_num} - {desc} -> {snippet}...")
                violations += 1

    if violations > 0:
        print(f"\n[FAILED] {violations} potential secrets detected! Store keys in Google Secret Manager or environment variables.")
        sys.exit(1)
    else:
        print("[SUCCESS] No committed secrets found. Repository is compliant.")
        sys.exit(0)

if __name__ == "__main__":
    main()
