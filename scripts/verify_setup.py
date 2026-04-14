# scripts/verify_setup.py
"""Verify that the local LLM setup is working correctly."""
import sys
from pathlib import Path

def check_pytorch():
    """Check PyTorch and GPU availability (CUDA or MPS)."""
    try:
        import torch
        print("✓ PyTorch installed")
        print(f"  Version: {torch.__version__}")

        if torch.backends.mps.is_available():
            print("✓ MPS (Apple Silicon) available")
            print("  Device: Apple Metal GPU")
            print("  Note: 4-bit quantization not supported on MPS, using FP16")
        elif torch.cuda.is_available():
            print("✓ CUDA available")
            print(f"  Device: {torch.cuda.get_device_name(0)}")
            print(f"  CUDA Version: {torch.version.cuda}")
        else:
            print("✗ No GPU backend available - will use CPU (slow)")
        return True
    except ImportError:
        print("✗ PyTorch not installed")
        return False

def check_transformers():
    """Check transformers library."""
    try:
        import transformers
        print(f"✓ Transformers installed (version {transformers.__version__})")
        return True
    except ImportError:
        print("✗ Transformers not installed")
        return False

def check_bitsandbytes():
    """Check bitsandbytes for quantization (optional on Apple Silicon)."""
    try:
        import torch
        is_mps = torch.backends.mps.is_available()
    except Exception:
        is_mps = False

    try:
        import bitsandbytes
        print(f"✓ BitsAndBytes installed (version {bitsandbytes.__version__})")
        return True
    except ImportError:
        if is_mps:
            print("⊘ BitsAndBytes not installed (not needed on Apple Silicon, using FP16)")
            return True  # Not a failure on MPS
        print("✗ BitsAndBytes not installed (4-bit quantization will not work)")
        return False

def check_other_deps():
    """Check other required dependencies."""
    deps = {
        "pandas": "pandas",
        "numpy": "numpy",
        "sqlparse": "sqlparse",
        "tqdm": "tqdm",
        "accelerate": "accelerate",
        "huggingface_hub": "huggingface_hub",
    }
    
    all_ok = True
    for name, module in deps.items():
        try:
            __import__(module)
            print(f"✓ {name} installed")
        except ImportError:
            print(f"✗ {name} not installed")
            all_ok = False
    
    return all_ok

def check_local_model():
    """Check if local_model.py can be imported."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from scripts.local_model import LocalChatModel
        print("✓ LocalChatModel class can be imported")
        return True
    except Exception as e:
        print(f"✗ Cannot import LocalChatModel: {e}")
        return False

def main():
    """Run all checks."""
    print("=" * 60)
    print("Local LLM Setup Verification")
    print("=" * 60)
    print()
    
    results = []
    results.append(("PyTorch & CUDA", check_pytorch()))
    print()
    results.append(("Transformers", check_transformers()))
    print()
    results.append(("BitsAndBytes", check_bitsandbytes()))
    print()
    results.append(("Other Dependencies", check_other_deps()))
    print()
    results.append(("Local Model Script", check_local_model()))
    print()
    
    print("=" * 60)
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("✓ All checks passed! Setup is ready.")
    else:
        print("✗ Some checks failed. Please install missing dependencies.")
        print("  Run: pip install -r requirements.txt")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

