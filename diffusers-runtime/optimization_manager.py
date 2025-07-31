"""
Pipeline optimization management for diffusion models.
"""
import os
from typing import Dict


class OptimizationManager:
    """Handles pipeline optimizations and memory management."""
    
    @staticmethod
    def parse_optimization_flags() -> Dict[str, bool]:
        """Parse environment variables for optimization control."""
        return {
            'use_low_cpu_mem': os.environ.get("ENABLE_LOW_CPU_MEM", "true").lower() == "true",
            'use_attention_slicing': os.environ.get("ENABLE_ATTENTION_SLICING", "true").lower() == "true",
            'use_vae_slicing': os.environ.get("ENABLE_VAE_SLICING", "true").lower() == "true",
            'use_cpu_offload': os.environ.get("ENABLE_CPU_OFFLOAD", "true").lower() == "true"
        }
    
    def apply_optimizations(self, pipeline, device_type: str, config: Dict[str, bool]):
        """Apply device-specific optimizations to the pipeline."""
        if device_type == "cuda":
            self._apply_cuda_optimizations(pipeline, config)
        elif device_type == "mps":
            self._apply_mps_optimizations(pipeline, config)
        # CPU doesn't need special optimizations for basic inference
    
    def _apply_cuda_optimizations(self, pipeline, config: Dict[str, bool]):
        """Apply CUDA-specific optimizations."""
        if config['use_attention_slicing'] and hasattr(pipeline, 'enable_attention_slicing'):
            pipeline.enable_attention_slicing()
            print("Enabled attention slicing")
        
        if config['use_vae_slicing'] and hasattr(pipeline, 'enable_vae_slicing'):
            pipeline.enable_vae_slicing()
            print("Enabled VAE slicing")
        
        if config['use_cpu_offload']:
            if hasattr(pipeline, 'enable_model_cpu_offload'):
                pipeline.enable_model_cpu_offload()
                print("Enabled model CPU offload")
            elif hasattr(pipeline, 'enable_sequential_cpu_offload'):
                pipeline.enable_sequential_cpu_offload()
                print("Enabled sequential CPU offload")
    
    def _apply_mps_optimizations(self, pipeline, config: Dict[str, bool]):
        """Apply MPS-specific optimizations."""
        if config['use_attention_slicing'] and hasattr(pipeline, 'enable_attention_slicing'):
            pipeline.enable_attention_slicing()
            print("Enabled attention slicing (MPS)")
        
        # Additional MPS memory optimizations (use with caution)
        if config['use_vae_slicing'] and hasattr(pipeline, 'enable_vae_slicing'):
            pipeline.enable_vae_slicing()
            print("Enabled VAE slicing (MPS)")