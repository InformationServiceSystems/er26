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


def get_device():
    """Detect the best available device (MPS for Apple Silicon, CUDA for NVIDIA, else CPU)."""
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda"
    return "cpu"


class LocalChatModel:
    def __init__(self, model_path: str, load_in_4bit: bool = True):
        """
        Initialize a local chat model.

        Args:
            model_path: Path to the model (local directory or HuggingFace hub name)
            load_in_4bit: If True, use 4-bit quantization (CUDA only).
                          On MPS/CPU this is ignored and FP16/FP32 is used instead.
        """
        self.device_type = get_device()
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)

        kwargs = {}

        # BitsAndBytes 4-bit quantization only works on CUDA
        if load_in_4bit and self.device_type == "cuda":
            from transformers import BitsAndBytesConfig
            kwargs.update(
                dict(
                    device_map="auto",
                    quantization_config=BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    ),
                )
            )
        elif self.device_type == "mps":
            # Apple Silicon: load in FP32 for numerical stability (FP16 causes NaN on long prompts)
            kwargs.update(dict(torch_dtype=torch.float32))
            if load_in_4bit:
                print("Note: 4-bit quantization not supported on MPS. Using FP32 instead.")
        else:
            kwargs.update(dict(device_map="auto", torch_dtype=torch.float16))

        print(f"Loading model on device: {self.device_type}")
        self.model = AutoModelForCausalLM.from_pretrained(model_path, **kwargs)

        # Move model to MPS explicitly (device_map="auto" doesn't support MPS)
        if self.device_type == "mps":
            self.model = self.model.to("mps")

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
                top_p=0.95,
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
        
        full_text = self.generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)
        # Strip the prompt to return only the generated response
        if full_text.startswith(prompt):
            return full_text[len(prompt):]
        # Fallback: try to find the last assistant marker for chat models
        for marker in ['<|start_header_id|>assistant<|end_header_id|>\n\n',
                        'assistant\n', '[/INST]']:
            idx = full_text.rfind(marker)
            if idx != -1:
                return full_text[idx + len(marker):]
        return full_text
    
    def generate_with_efficiency(self, prompt: str, max_new_tokens: int = 256, temperature: float = 0.7) -> tuple:
        """
        Generate text and compute cognitive efficiency metrics in a single inference call.

        Args:
            prompt: Input text prompt
            max_new_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature

        Returns:
            tuple: (generated_text, efficiency_metrics_dict)
        """
        if not HAS_EFFICIENCY:
            text = self.generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)
            return text, {}

        from scripts.cognitive_efficiency import ActivationTracker
        tracker = ActivationTracker()
        try:
            tracker.register_hooks(self.model)
            inputs = self.tokenizer(prompt, return_tensors="pt")
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
            metrics = tracker.compute_efficiency_metrics()

            num_input_tokens = inputs['input_ids'].shape[1]
            num_output_tokens = output_ids.shape[1] - num_input_tokens
            metrics['num_input_tokens'] = num_input_tokens
            metrics['num_output_tokens'] = num_output_tokens
            metrics['total_tokens_processed'] = num_input_tokens + num_output_tokens

            return text, metrics
        except Exception as e:
            print(f"Warning: Efficiency tracking failed: {e}")
            text = self.generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)
            return text, {}
        finally:
            tracker.remove_hooks()
            tracker.reset()

    def generate_batch(self, prompt: str, num_sequences: int = 5, max_new_tokens: int = 256, temperature: float = 0.7) -> tuple:
        """
        Generate multiple outputs from the same prompt in a single model.generate() call.

        Args:
            prompt: Input text prompt
            num_sequences: Number of output sequences to generate
            max_new_tokens: Maximum number of tokens to generate per sequence
            temperature: Sampling temperature

        Returns:
            tuple: (list_of_texts, list_of_metrics_dicts)
        """
        inputs = self.tokenizer(prompt, return_tensors="pt")
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        tracker = None
        if HAS_EFFICIENCY:
            from scripts.cognitive_efficiency import ActivationTracker
            tracker = ActivationTracker()

        try:
            if tracker:
                tracker.register_hooks(self.model)

            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=True,
                    temperature=temperature,
                    num_return_sequences=num_sequences,
                    pad_token_id=self.tokenizer.eos_token_id,
                )

            texts = [
                self.tokenizer.decode(output_ids[i], skip_special_tokens=True)
                for i in range(num_sequences)
            ]

            if tracker:
                metrics = tracker.compute_efficiency_metrics()
                num_input_tokens = inputs['input_ids'].shape[1]
                num_output_tokens = output_ids.shape[1] - num_input_tokens
                metrics['num_input_tokens'] = num_input_tokens
                metrics['num_output_tokens'] = num_output_tokens
                metrics['total_tokens_processed'] = num_input_tokens + num_output_tokens
                metrics_list = [metrics] * num_sequences
            else:
                metrics_list = [{} for _ in range(num_sequences)]

            return texts, metrics_list

        except torch.cuda.OutOfMemoryError:
            print(f"Warning: OOM with {num_sequences} sequences, falling back to sequential generation")
            torch.cuda.empty_cache()
            if tracker:
                tracker.remove_hooks()
                tracker.reset()
            texts = []
            metrics_list = []
            for _ in range(num_sequences):
                text, metrics = self.generate_with_efficiency(
                    prompt, max_new_tokens=max_new_tokens, temperature=temperature
                )
                texts.append(text)
                metrics_list.append(metrics)
            return texts, metrics_list

        finally:
            if tracker:
                tracker.remove_hooks()
                tracker.reset()

