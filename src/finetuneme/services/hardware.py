"""
Hardware detection service for GPU compatibility checking.
Implements "The Gatekeeper" logic from gpu_compatibility_matrix.md
"""
from dataclasses import dataclass
from typing import Optional, Literal
import subprocess
import re
import os


@dataclass
class HardwareStatus:
    """Hardware status information"""
    tier: Literal["GREEN", "YELLOW", "RED"]
    gpu_name: str
    compute_capability: Optional[float] = None
    vram_gb: Optional[float] = None
    driver_version: Optional[str] = None
    pytorch_mode: Optional[Literal["stable", "nightly", "cpu"]] = None
    cuda_available: bool = False
    message: str = ""
    recommendation: Optional[str] = None


def get_nvidia_gpu_info() -> Optional[dict]:
    """
    Query nvidia-smi for GPU information.

    Returns:
        Dict with GPU info or None if nvidia-smi not available
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

            # Parse first GPU (index 0)
            # Example output: "NVIDIA GeForce RTX 5080, 16384 MiB, 565.51, 10.0"
            parts = [p.strip() for p in lines[0].split(',')]

            if len(parts) >= 4:
                name = parts[0]
                vram_mb = float(parts[1].split()[0])  # "16384 MiB" -> 16384
                driver = parts[2]
                cc = float(parts[3])

                return {
                    "vendor": "nvidia",
                    "name": name,
                    "vram_gb": round(vram_mb / 1024, 1),
                    "driver_version": driver,
                    "compute_capability": cc
                }
    except FileNotFoundError:
        # nvidia-smi not found (no NVIDIA GPU or drivers not installed)
        pass
    except subprocess.TimeoutExpired:
        print("Warning: nvidia-smi query timed out")
    except Exception as e:
        print(f"Error querying nvidia-smi: {str(e)}")

    return None


def detect_amd_gpu() -> bool:
    """
    Detect if an AMD GPU is present.

    Returns:
        True if AMD GPU detected, False otherwise
    """
    try:
        # Try rocm-smi for AMD GPUs
        result = subprocess.run(
            ["rocm-smi", "--showproductname"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout:
            return True
    except:
        pass

    # Fallback: Check common AMD GPU indicators on Windows
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
                    return True
        except:
            pass

    return False


def detect_hardware_status() -> HardwareStatus:
    """
    Main hardware detection function.
    Implements the logic from gpu_compatibility_matrix.md

    Returns:
        HardwareStatus with tier (GREEN/YELLOW/RED) and details
    """

    # 1. Check for NVIDIA GPU first
    gpu_info = get_nvidia_gpu_info()

    if gpu_info:
        name = gpu_info["name"]
        cc = gpu_info["compute_capability"]
        vram_gb = gpu_info["vram_gb"]
        driver = gpu_info["driver_version"]

        # 2. Blackwell (RTX 50-series) - YELLOW tier
        if cc >= 10.0:
            if vram_gb >= 12:
                return HardwareStatus(
                    tier="YELLOW",
                    gpu_name=name,
                    compute_capability=cc,
                    vram_gb=vram_gb,
                    driver_version=driver,
                    pytorch_mode="nightly",
                    cuda_available=True,
                    message="Blackwell GPU detected - Experimental support",
                    recommendation="Using PyTorch Nightly. Consider cloud fallback (Groq/OpenAI) if issues occur."
                )
            else:
                return HardwareStatus(
                    tier="RED",
                    gpu_name=name,
                    compute_capability=cc,
                    vram_gb=vram_gb,
                    driver_version=driver,
                    message=f"Insufficient VRAM for Blackwell ({vram_gb}GB detected, 12GB minimum)",
                    recommendation="Use cloud providers exclusively (Groq/OpenAI/Anthropic)"
                )

        # 3. Modern NVIDIA (RTX 20/30/40 series, CC 7.0-9.x) - GREEN tier
        if 7.0 <= cc < 10.0:
            if vram_gb >= 6:
                return HardwareStatus(
                    tier="GREEN",
                    gpu_name=name,
                    compute_capability=cc,
                    vram_gb=vram_gb,
                    driver_version=driver,
                    pytorch_mode="stable",
                    cuda_available=True,
                    message="GPU fully supported",
                    recommendation=None
                )
            else:
                return HardwareStatus(
                    tier="RED",
                    gpu_name=name,
                    compute_capability=cc,
                    vram_gb=vram_gb,
                    driver_version=driver,
                    message=f"Insufficient VRAM ({vram_gb}GB detected, 6GB minimum required)",
                    recommendation="Use cloud providers or install smaller Ollama models (e.g., llama3.2:1b)"
                )

        # 4. Legacy NVIDIA (GTX 10-series and older, CC < 7.0) - RED tier
        if cc < 7.0:
            return HardwareStatus(
                tier="RED",
                gpu_name=name,
                compute_capability=cc,
                vram_gb=vram_gb,
                driver_version=driver,
                message=f"Legacy GPU (CC {cc}) - PyTorch 2.0+ requires CC >= 7.0",
                recommendation="Cloud Only Mode - Ollama will not work. Use Groq/OpenAI/Anthropic instead."
            )

    # 5. Check for AMD GPU
    if detect_amd_gpu():
        return HardwareStatus(
            tier="RED",
            gpu_name="AMD GPU Detected",
            message="AMD GPUs not supported - ROCm integration not yet implemented",
            recommendation="Cloud Only Mode - Use Groq (fastest), OpenAI, or Anthropic"
        )

    # 6. No GPU detected (CPU-only mode)
    return HardwareStatus(
        tier="RED",
        gpu_name="No GPU",
        message="No GPU detected - CPU-only mode",
        recommendation="Ollama can run in CPU mode (very slow). Recommended: Use cloud providers for faster generation."
    )


def check_pytorch_cuda_availability() -> dict:
    """
    Check if PyTorch is installed and has CUDA support.

    Returns:
        Dict with PyTorch status
    """
    try:
        import torch

        return {
            "installed": True,
            "version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "current_device": torch.cuda.current_device() if torch.cuda.is_available() else None
        }
    except ImportError:
        return {
            "installed": False,
            "version": None,
            "cuda_available": False,
            "cuda_version": None,
            "device_count": 0,
            "current_device": None
        }


def get_pytorch_mode_from_env() -> Optional[str]:
    """
    Get PyTorch mode from environment variable.

    Returns:
        "stable", "nightly", "cpu", or None
    """
    from finetuneme.core.config import settings

    # Check if bypass is enabled
    if os.getenv("FTM_BYPASS_HARDWARE_CHECK", "").lower() == "true":
        return os.getenv("FTM_FORCE_PYTORCH_MODE", "stable")

    # Read from .env file via settings
    mode = os.getenv("FTM_PYTORCH_MODE")
    if mode in ["stable", "nightly", "cpu"]:
        return mode

    return None


def validate_hardware_for_ollama() -> tuple[bool, str]:
    """
    Validate if hardware is suitable for Ollama local inference.

    Returns:
        Tuple of (is_valid, message)
    """
    status = detect_hardware_status()

    if status.tier == "GREEN":
        return True, "Hardware fully supports Ollama local inference"
    elif status.tier == "YELLOW":
        return True, "Hardware supports Ollama (experimental). Cloud providers recommended for stability."
    else:  # RED
        return False, f"{status.message}. Please use cloud providers (Groq/OpenAI/Anthropic)."


# CLI testing
if __name__ == "__main__":
    print("=== FineTuneMe Hardware Detection ===\n")

    status = detect_hardware_status()

    tier_emoji = {
        "GREEN": "✅",
        "YELLOW": "⚡",
        "RED": "⛔"
    }

    print(f"{tier_emoji[status.tier]} Tier: {status.tier}")
    print(f"GPU: {status.gpu_name}")

    if status.compute_capability:
        print(f"Compute Capability: {status.compute_capability}")
    if status.vram_gb:
        print(f"VRAM: {status.vram_gb}GB")
    if status.driver_version:
        print(f"Driver: {status.driver_version}")
    if status.pytorch_mode:
        print(f"PyTorch Mode: {status.pytorch_mode}")

    print(f"\nMessage: {status.message}")
    if status.recommendation:
        print(f"Recommendation: {status.recommendation}")

    print("\n=== PyTorch Status ===")
    pytorch_info = check_pytorch_cuda_availability()
    if pytorch_info["installed"]:
        print(f"PyTorch Version: {pytorch_info['version']}")
        print(f"CUDA Available: {pytorch_info['cuda_available']}")
        if pytorch_info["cuda_version"]:
            print(f"CUDA Version: {pytorch_info['cuda_version']}")
    else:
        print("PyTorch not installed")

    print("\n=== Ollama Validation ===")
    is_valid, message = validate_hardware_for_ollama()
    print(f"Valid: {is_valid}")
    print(f"Message: {message}")
