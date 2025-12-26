"""
Pre-installation hardware check for FineTuneMe Local V2.0

This script runs BEFORE creating the virtual environment.
Uses ONLY Python standard library (no dependencies).

Detects GPU and determines which PyTorch version to install:
- Blackwell (RTX 50-series) -> PyTorch Nightly
- Modern NVIDIA (RTX 20/30/40) -> PyTorch Stable
- Legacy/AMD/None -> CPU-only PyTorch
"""

import subprocess
import json
import sys
import os


def check_nvidia_gpu():
    """
    Detect NVIDIA GPU using nvidia-smi.
    Returns dict with GPU info or None if not available.
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version,compute_cap",
                "--format=csv,noheader"
            ],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split('\n')
            if not lines:
                return None

            # Parse first GPU
            parts = [p.strip() for p in lines[0].split(',')]

            if len(parts) >= 4:
                name = parts[0]
                vram_mb = float(parts[1].split()[0])
                driver = parts[2]
                cc_str = parts[3]

                try:
                    cc = float(cc_str)
                except ValueError:
                    cc = 0.0

                return {
                    "vendor": "nvidia",
                    "name": name,
                    "vram_gb": round(vram_mb / 1024, 1),
                    "driver_version": driver,
                    "compute_capability": cc
                }
    except FileNotFoundError:
        # nvidia-smi not found
        pass
    except subprocess.TimeoutExpired:
        print("[WARNING] nvidia-smi query timed out")
    except Exception as e:
        print(f"[WARNING] Error querying nvidia-smi: {str(e)}")

    return None


def check_amd_gpu():
    """
    Detect AMD GPU.
    Returns True if AMD GPU detected, False otherwise.
    """
    try:
        # Try rocm-smi
        result = subprocess.run(
            ["rocm-smi", "--showproductname"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout:
            # Parse AMD GPU name
            name_match = None
            for line in result.stdout.split('\n'):
                if "Card series" in line or "Card model" in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        name_match = parts[1].strip()
                        break

            return {
                "vendor": "amd",
                "name": name_match or "AMD GPU",
                "vram_gb": None,
                "driver_version": None
            }
    except:
        pass

    # Fallback: Check via wmic on Windows
    if os.name == 'nt':
        try:
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                output = result.stdout.lower()
                if "amd" in output or "radeon" in output:
                    # Extract actual name
                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        if line and "name" not in line.lower():
                            if "amd" in line.lower() or "radeon" in line.lower():
                                return {
                                    "vendor": "amd",
                                    "name": line,
                                    "vram_gb": None,
                                    "driver_version": None
                                }
        except:
            pass

    return None


def determine_tier(gpu_info):
    """
    Determine hardware tier and PyTorch mode based on GPU info.

    Returns:
        Tuple of (tier, pytorch_mode, message, recommendation)
    """
    if not gpu_info:
        return (
            "RED",
            "cpu",
            "No GPU detected - CPU-only mode",
            "Ollama can run in CPU mode (very slow). Recommended: Use cloud providers."
        )

    vendor = gpu_info.get("vendor")
    name = gpu_info.get("name", "Unknown GPU")

    # AMD GPU
    if vendor == "amd":
        return (
            "RED",
            "cpu",
            f"{name} - AMD GPUs not supported",
            "Cloud Only Mode - Use Groq (fastest), OpenAI, or Anthropic"
        )

    # NVIDIA GPU
    if vendor == "nvidia":
        cc = gpu_info.get("compute_capability", 0.0)
        vram_gb = gpu_info.get("vram_gb", 0.0)

        # Blackwell (RTX 50-series) - YELLOW tier
        if cc >= 10.0:
            if vram_gb >= 12:
                return (
                    "YELLOW",
                    "nightly",
                    f"{name} detected - Blackwell GPU (CC {cc})",
                    "Experimental support with PyTorch Nightly. Cloud fallback recommended."
                )
            else:
                return (
                    "RED",
                    "cpu",
                    f"{name} - Insufficient VRAM ({vram_gb}GB, need 12GB+)",
                    "Use cloud providers exclusively"
                )

        # Modern NVIDIA (CC 7.0 - 9.x) - GREEN tier
        if 7.0 <= cc < 10.0:
            if vram_gb >= 6:
                return (
                    "GREEN",
                    "stable",
                    f"{name} - Fully supported (CC {cc}, {vram_gb}GB VRAM)",
                    None
                )
            else:
                return (
                    "RED",
                    "cpu",
                    f"{name} - Insufficient VRAM ({vram_gb}GB, need 6GB+)",
                    "Use cloud providers or smaller Ollama models"
                )

        # Legacy NVIDIA (CC < 7.0) - RED tier
        if cc < 7.0:
            return (
                "RED",
                "cpu",
                f"{name} - Legacy GPU (CC {cc}) - PyTorch 2.0+ requires CC >= 7.0",
                "Cloud Only Mode - Ollama will not work"
            )

    # Unknown configuration
    return (
        "RED",
        "cpu",
        f"{name} - Unknown GPU configuration",
        "Use cloud providers for safety"
    )


def main():
    """Main pre-install check"""
    print("=" * 60)
    print("FineTuneMe Local V2.0 - Pre-Installation Hardware Check")
    print("=" * 60)
    print()

    # Check for NVIDIA GPU first
    print("Checking for NVIDIA GPU...")
    gpu_info = check_nvidia_gpu()

    # If no NVIDIA, check for AMD
    if not gpu_info:
        print("No NVIDIA GPU found. Checking for AMD GPU...")
        gpu_info = check_amd_gpu()

    # Determine tier
    tier, pytorch_mode, message, recommendation = determine_tier(gpu_info)

    # Print results
    tier_symbols = {
        "GREEN": "✅ [SUPPORTED]",
        "YELLOW": "⚡ [EXPERIMENTAL]",
        "RED": "⛔ [UNSUPPORTED]"
    }

    print()
    print(tier_symbols[tier])
    print(f"  {message}")
    if recommendation:
        print(f"  Recommendation: {recommendation}")
    print()

    # Create result file for install.bat to read
    result = {
        "tier": tier,
        "pytorch_mode": pytorch_mode,
        "gpu_name": gpu_info.get("name") if gpu_info else "No GPU",
        "compute_capability": gpu_info.get("compute_capability") if gpu_info else None,
        "vram_gb": gpu_info.get("vram_gb") if gpu_info else None,
        "driver_version": gpu_info.get("driver_version") if gpu_info else None,
        "message": message,
        "recommendation": recommendation
    }

    # Write to JSON file
    try:
        with open("hardware_status.json", "w") as f:
            json.dump(result, f, indent=2)
        print("[INFO] Hardware status saved to hardware_status.json")
    except Exception as e:
        print(f"[WARNING] Failed to write hardware_status.json: {e}")

    # Print installation plan
    print()
    print("=" * 60)
    print("Installation Plan:")
    print("=" * 60)

    if pytorch_mode == "nightly":
        print("  PyTorch: NIGHTLY BUILD (for Blackwell GPUs)")
        print("  Command: pip install torch --pre --index-url https://download.pytorch.org/whl/nightly/cu124")
    elif pytorch_mode == "stable":
        print("  PyTorch: STABLE BUILD (recommended)")
        print("  Command: pip install torch==2.1.0+cu121 --index-url https://download.pytorch.org/whl/cu121")
    else:  # cpu
        print("  PyTorch: CPU-ONLY BUILD")
        print("  Command: pip install torch")
        print()
        if tier == "RED":
            print("  [!] WARNING: Local Ollama inference will NOT work")
            print("  [!] You MUST use cloud providers (Groq/OpenAI/Anthropic)")

    print("=" * 60)
    print()

    # Interactive check for RED tier
    if tier == "RED":
        print()
        print("[!] NO COMPATIBLE NVIDIA GPU DETECTED")
        print()
        print("Options:")
        print("[1] Continue with CPU Mode (Warning: Very Slow)")
        print("[2] Abort Installation (Return to Cloud Mode)")
        print()
        
        while True:
            try:
                choice = input("Enter your choice [1/2]: ").strip()
            except EOFError:
                # Handle non-interactive environments (like CI/CD) by defaulting to CPU
                print("[WARNING] Non-interactive environment detected. Defaulting to CPU mode.")
                choice = "1"

            if choice == "1":
                print("[INFO] Continuing with CPU mode...")
                break
            elif choice == "2":
                print("[INFO] Aborting installation...")
                sys.exit(99)
            else:
                print("Invalid choice. Please enter 1 or 2.")

    # Exit codes for install.bat
    # 0 = GREEN, 1 = YELLOW, 2 = RED
    exit_codes = {"GREEN": 0, "YELLOW": 1, "RED": 2}
    sys.exit(exit_codes[tier])


if __name__ == "__main__":
    main()
