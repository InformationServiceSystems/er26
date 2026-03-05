# scripts/test_model.py
"""Quick test script to verify a model loads and generates text."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.local_model import LocalChatModel

def main():
    """Test model loading and generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test local model loading and generation")
    parser.add_argument(
        "--model",
        type=str,
        default="models/llama3-8b",
        help="Path to model (local or HuggingFace hub name)"
    )
    parser.add_argument(
        "--use-4bit",
        action="store_true",
        default=True,
        help="Use 4-bit quantization (default: True)"
    )
    parser.add_argument(
        "--fp16",
        action="store_true",
        help="Use FP16 instead of 4-bit"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="Write a SQL query that selects all customers from table Customers.",
        help="Test prompt"
    )
    
    args = parser.parse_args()
    
    load_in_4bit = args.use_4bit and not args.fp16
    
    print("=" * 60)
    print("Testing Local Model")
    print("=" * 60)
    print(f"Model: {args.model}")
    print(f"Quantization: {'4-bit' if load_in_4bit else 'FP16'}")
    print(f"Prompt: {args.prompt}")
    print("=" * 60)
    print()
    
    try:
        print("Loading model...")
        model = LocalChatModel(args.model, load_in_4bit=load_in_4bit)
        print("✓ Model loaded successfully")
        print()
        
        print("Generating response...")
        response = model.generate(args.prompt, max_new_tokens=128, temperature=0.7)
        print()
        print("Response:")
        print("-" * 60)
        print(response)
        print("-" * 60)
        print()
        print("✓ Test completed successfully!")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

