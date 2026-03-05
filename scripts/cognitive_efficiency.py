# scripts/cognitive_efficiency.py
"""Track and compute cognitive efficiency metrics (neuron activations)."""
import torch
import torch.nn as nn
from typing import Dict, List, Tuple
import numpy as np

class ActivationTracker:
    """Track neuron activations during model forward pass."""
    
    def __init__(self):
        self.activations = []
        self.hooks = []
        self.total_neurons = 0
        self.layer_names = []
    
    def register_hooks(self, model):
        """Register forward hooks to track activations."""
        self.activations = []
        self.hooks = []
        
        def make_hook(name):
            def hook(module, input, output):
                # Track activations in feed-forward layers (focus on MLP layers)
                # Only track layers that are part of feed-forward networks
                if 'mlp' in name.lower() or 'feed_forward' in name.lower() or 'ffn' in name.lower():
                    # Use a threshold to determine "active" neurons (not just non-zero)
                    # This is more realistic - neurons with significant activation
                    threshold = 0.01  # Threshold for considering a neuron "active"
                    
                    if len(output.shape) >= 2:
                        # Count significantly activated neurons
                        if len(output.shape) == 3:  # (batch, seq_len, hidden_size)
                            for token_idx in range(output.shape[1]):
                                token_activations = output[0, token_idx, :]
                                # Count neurons above threshold (absolute value)
                                active_neurons = (torch.abs(token_activations) > threshold).sum().item()
                                total_neurons = token_activations.numel()
                                avg_activation = token_activations.abs().mean().item()
                                self.activations.append({
                                    'layer': name,
                                    'token_idx': token_idx,
                                    'active_neurons': active_neurons,
                                    'total_neurons': total_neurons,
                                    'activation_rate': active_neurons / total_neurons if total_neurons > 0 else 0,
                                    'avg_activation': avg_activation
                                })
                        elif len(output.shape) == 2:  # (batch, hidden_size)
                            token_activations = output[0, :]
                            threshold = 0.01
                            active_neurons = (torch.abs(token_activations) > threshold).sum().item()
                            total_neurons = token_activations.numel()
                            avg_activation = token_activations.abs().mean().item()
                            self.activations.append({
                                'layer': name,
                                'token_idx': 0,
                                'active_neurons': active_neurons,
                                'total_neurons': total_neurons,
                                'activation_rate': active_neurons / total_neurons if total_neurons > 0 else 0,
                                'avg_activation': avg_activation
                            })
            return hook
        
        # Register hooks on feed-forward (MLP) layers in transformer blocks
        for name, module in model.named_modules():
            # Focus on MLP/feed-forward layers in transformer architecture
            if isinstance(module, nn.Linear) and ('mlp' in name.lower() or 'feed_forward' in name.lower() or 'ffn' in name.lower() or 'gate' in name.lower() or 'up_proj' in name.lower() or 'down_proj' in name.lower()):
                hook = module.register_forward_hook(make_hook(name))
                self.hooks.append(hook)
                self.layer_names.append(name)
                # Estimate total neurons (use MLP output dimension)
                if self.total_neurons == 0 and hasattr(module, 'out_features'):
                    self.total_neurons = module.out_features
    
    def remove_hooks(self):
        """Remove all registered hooks."""
        for hook in self.hooks:
            hook.remove()
        self.hooks = []
    
    def compute_efficiency_metrics(self) -> Dict:
        """
        Compute cognitive efficiency metrics from tracked activations.
        
        Returns:
            dict with efficiency metrics
        """
        if not self.activations:
            return {
                'avg_neurons_per_token': 0,
                'avg_activation_rate': 0.0,
                'total_activations': 0,
                'total_tokens': 0,
                'efficiency_score': 0.0
            }
        
        # Aggregate by token
        token_stats = {}
        for act in self.activations:
            token_idx = act['token_idx']
            if token_idx not in token_stats:
                token_stats[token_idx] = {
                    'total_active': 0,
                    'total_neurons': 0,
                    'layers': 0
                }
            token_stats[token_idx]['total_active'] += act['active_neurons']
            token_stats[token_idx]['total_neurons'] += act['total_neurons']
            token_stats[token_idx]['layers'] += 1
        
        # Compute averages
        num_tokens = len(token_stats)
        if num_tokens == 0:
            return {
                'avg_neurons_per_token': 0,
                'avg_activation_rate': 0.0,
                'total_activations': 0,
                'total_tokens': 0,
                'efficiency_score': 0.0
            }
        
        total_active = sum(stats['total_active'] for stats in token_stats.values())
        total_neurons = sum(stats['total_neurons'] for stats in token_stats.values())
        
        avg_neurons_per_token = total_active / num_tokens if num_tokens > 0 else 0
        avg_activation_rate = total_active / total_neurons if total_neurons > 0 else 0.0
        
        # Efficiency score: lower activation rate = more efficient
        # Normalize to 0-1 scale where 1 = most efficient (lowest activation)
        efficiency_score = 1.0 - avg_activation_rate
        
        return {
            'avg_neurons_per_token': avg_neurons_per_token,
            'avg_activation_rate': avg_activation_rate,
            'activation_percentage': avg_activation_rate * 100,
            'total_activations': total_active,
            'total_tokens': num_tokens,
            'efficiency_score': efficiency_score,
            'num_layers_tracked': len(self.layer_names)
        }
    
    def reset(self):
        """Reset tracked activations."""
        self.activations = []


def compute_model_efficiency(model, tokenizer, prompt: str, max_new_tokens: int = 256) -> Dict:
    """
    Compute cognitive efficiency for a single generation.
    
    Args:
        model: The language model
        tokenizer: The tokenizer
        prompt: Input prompt
        max_new_tokens: Maximum tokens to generate
        
    Returns:
        dict with efficiency metrics
    """
    tracker = ActivationTracker()
    
    try:
        # Register hooks
        tracker.register_hooks(model)
        
        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt")
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Generate with tracking
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                pad_token_id=tokenizer.eos_token_id,
            )
        
        # Compute metrics
        metrics = tracker.compute_efficiency_metrics()
        
        # Add generation info
        num_input_tokens = inputs['input_ids'].shape[1]
        num_output_tokens = output_ids.shape[1] - num_input_tokens
        metrics['num_input_tokens'] = num_input_tokens
        metrics['num_output_tokens'] = num_output_tokens
        metrics['total_tokens_processed'] = num_input_tokens + num_output_tokens
        
    finally:
        tracker.remove_hooks()
        tracker.reset()
    
    return metrics

