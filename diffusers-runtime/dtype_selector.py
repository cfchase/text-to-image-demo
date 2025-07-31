"""
Data type selection and fallback logic for diffusion models.
"""
import os
from typing import Union
import torch
from diffusers import DiffusionPipeline
from device_manager import DeviceManager


class DtypeSelector:
    """Handles intelligent dtype selection with hardware-aware fallbacks."""
    
    def __init__(self, model_id: str, device_manager: DeviceManager):
        self.model_id = model_id
        self.device_manager = device_manager
    
    def get_model_native_dtype(self) -> torch.dtype:
        """Get the model's original training dtype from config."""
        try:
            config = DiffusionPipeline.load_config(self.model_id)
            dtype_str = getattr(config, 'torch_dtype', None)
            
            if dtype_str == 'torch.bfloat16':
                return torch.bfloat16
            elif dtype_str == 'torch.float16':
                return torch.float16
            else:
                return torch.float32
        except Exception as e:
            print(f"Could not determine model native dtype: {e}")
            return torch.float32
    
    def _intelligent_dtype_selection(self, device_type: str) -> torch.dtype:
        """Automatically select the best dtype based on hardware and model."""
        if device_type == "cuda":
            # Priority: bfloat16 -> model native -> float16 -> float32
            if self.device_manager.check_bfloat16_support():
                print("DTYPE=auto: Selected bfloat16 (hardware optimal)")
                return torch.bfloat16
            
            model_native = self.get_model_native_dtype()
            if model_native != torch.float32:
                print(f"DTYPE=auto: Selected {model_native} (model native)")
                return model_native
            
            print("DTYPE=auto: Selected float16 (CUDA fallback)")
            return torch.float16
            
        elif device_type == "mps":
            # MPS: model native -> float32 (avoid float16 instability)
            model_native = self.get_model_native_dtype()
            if model_native == torch.float32:
                print("DTYPE=auto: Selected float32 (MPS stable)")
                return torch.float32
            else:
                print(f"DTYPE=auto: Selected float32 (MPS override from {model_native})")
                return torch.float32
                
        else:  # CPU
            # CPU: model native -> float32
            model_native = self.get_model_native_dtype()
            print(f"DTYPE=auto: Selected {model_native} (CPU)")
            return model_native
    
    def _get_dtype_with_fallback(self, target_dtype: torch.dtype, device_type: str) -> torch.dtype:
        """Get target dtype with intelligent fallback if unsupported."""
        if target_dtype == torch.bfloat16:
            if device_type == "cuda" and self.device_manager.check_bfloat16_support():
                print(f"DTYPE=bfloat16: Using bfloat16")
                return torch.bfloat16
            else:
                print(f"DTYPE=bfloat16: Hardware unsupported, falling back")
                # Fallback chain: model native -> float16 -> float32
                model_native = self.get_model_native_dtype()
                if model_native != torch.float32 and device_type == "cuda":
                    print(f"DTYPE=bfloat16: Fallback to {model_native}")
                    return model_native
                elif device_type == "cuda":
                    print(f"DTYPE=bfloat16: Fallback to float16")
                    return torch.float16
                else:
                    print(f"DTYPE=bfloat16: Fallback to float32")
                    return torch.float32
                    
        elif target_dtype == torch.float16:
            if device_type == "cuda":
                print(f"DTYPE=float16: Using float16")
                return torch.float16
            else:
                print(f"DTYPE=float16: Device unsupported, falling back")
                # Fallback: model native -> float32
                model_native = self.get_model_native_dtype()
                print(f"DTYPE=float16: Fallback to {model_native}")
                return model_native
                
        else:  # target_dtype == torch.float32 or other
            return target_dtype
    
    def determine_torch_dtype(self, device_type: str) -> torch.dtype:
        """Determine the appropriate torch dtype based on DTYPE environment variable."""
        dtype_env = os.environ.get("DTYPE", "auto").lower()
        
        if dtype_env == "float32":
            print("DTYPE=float32: Using float32")
            return torch.float32
        elif dtype_env == "float16":
            return self._get_dtype_with_fallback(torch.float16, device_type)
        elif dtype_env == "bfloat16":
            return self._get_dtype_with_fallback(torch.bfloat16, device_type)
        elif dtype_env == "native":
            model_native = self.get_model_native_dtype()
            print(f"DTYPE=native: Using {model_native}")
            return model_native
        else:  # "auto" or invalid value
            return self._intelligent_dtype_selection(device_type)