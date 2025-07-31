"""
Device management and hardware detection for diffusion models.
"""
from typing import Tuple, Dict, Any
import torch


class DeviceManager:
    """Handles device detection and hardware capability assessment."""
    
    @staticmethod
    def detect_device() -> Tuple[torch.device, str]:
        """Determine the best available device."""
        if torch.cuda.is_available():
            return torch.device("cuda"), "cuda"
        elif torch.backends.mps.is_available():
            return torch.device("mps"), "mps"
        else:
            return torch.device("cpu"), "cpu"
    
    @staticmethod
    def check_bfloat16_support() -> bool:
        """Check if hardware supports bfloat16 operations."""
        if not torch.cuda.is_available():
            return False
        
        try:
            # Check if GPU supports bfloat16 operations
            gpu_supports_bf16 = torch.cuda.is_bf16_supported()
            
            # Check compute capability (Ampere+ is 8.0+, optimal for bfloat16)
            capability = torch.cuda.get_device_capability()
            ampere_or_newer = capability[0] >= 8
            
            return gpu_supports_bf16 and ampere_or_newer
        except Exception:
            return False
    
    @staticmethod
    def get_device_capabilities() -> Dict[str, Any]:
        """Get detailed device capabilities for debugging."""
        capabilities = {
            "cuda_available": torch.cuda.is_available(),
            "mps_available": torch.backends.mps.is_available(),
        }
        
        if torch.cuda.is_available():
            try:
                capabilities.update({
                    "cuda_device_count": torch.cuda.device_count(),
                    "cuda_device_name": torch.cuda.get_device_name(),
                    "cuda_compute_capability": torch.cuda.get_device_capability(),
                    "bfloat16_supported": torch.cuda.is_bf16_supported(),
                })
            except Exception as e:
                capabilities["cuda_error"] = str(e)
        
        return capabilities