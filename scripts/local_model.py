# scripts/local_model.py
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import sys
from pathlib import Path

# Import cognitive efficiency tracker
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from scripts.cognitive_efficiency import compute_model_efficiency
    HAS_EFFICIENCY = True
except ImportError:
    HAS_EFFICIENCY = False

class LocalChatModel:
    def __init__(self, model_path: str, load_in_4bit: bool = True):
        """
        Initialize a local chat model.
        
        Args:
            model_path: Path to the model (local directory or HuggingFace hub name)
            load_in_4bit: If True, use 4-bit quantization. If False, use FP16.
        """
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)

        kwargs = {
            "device_map": "auto",
        }

        if load_in_4bit:
            from transformers import BitsAndBytesConfig
            kwargs.update(
                dict(
                    quantization_config=BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    ),
                )
            )
        else:
            kwargs.update(
                dict(
                    torch_dtype=torch.float16,
                )
            )

        self.model = AutoModelForCausalLM.from_pretrained(model_path, **kwargs)
        
        # Set pad token if not already set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def generate(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.7) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: Input text prompt
            max_new_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (higher = more random)
            
        Returns:
            Generated text (full response including prompt)
        """
        inputs = self.tokenizer(prompt, return_tensors="pt")
        # Get the device of the first model parameter (works with device_map="auto")
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=temperature,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return text
    
    def generate_chat(self, messages: list, max_new_tokens: int = 256, temperature: float = 0.7) -> str:
        """
        Generate response from chat messages (for chat-formatted models).
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            max_new_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated response text
        """
        # Format messages for chat template
        if hasattr(self.tokenizer, 'apply_chat_template'):
            prompt = self.tokenizer.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
        else:
            # Fallback: simple formatting
            prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
            prompt += "\nassistant: "
        
        return self.generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)
    
    def generate_with_efficiency(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.7) -> tuple:
        """
        Generate text and compute cognitive efficiency metrics.
        
        Args:
            prompt: Input text prompt
            max_new_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            
        Returns:
            tuple: (generated_text, efficiency_metrics_dict)
        """
        if not HAS_EFFICIENCY:
            # Fallback to regular generation
            text = self.generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)
            return text, {}
        
        try:
            # Compute efficiency metrics
            efficiency_metrics = compute_model_efficiency(
                self.model, 
                self.tokenizer, 
                prompt, 
                max_new_tokens
            )
            
            # Also get the generated text
            text = self.generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)
            
            return text, efficiency_metrics
        except Exception as e:
            # If efficiency tracking fails, fall back to regular generation
            print(f"Warning: Efficiency tracking failed: {e}")
            text = self.generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)
            return text, {}

