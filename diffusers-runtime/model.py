import os
import io
import base64
import argparse

from typing import Dict, Union
import torch
from diffusers import DiffusionPipeline
from accelerate import init_empty_weights, load_checkpoint_and_dispatch

from kserve import (
    Model,
    ModelServer,
    model_server,
    InferRequest,
    InferResponse,
)
from kserve.errors import InvalidInput


class DiffusersModel(Model):
    def __init__(self, name: str):
        super().__init__(name)
        self.model_id = os.environ.get("MODEL_ID", default="/mnt/models")
        self.pipeline = None
        self.refiner = None
        self.ready = False
        self.load()

    def _parse_optimization_flags(self):
        """Parse environment variables for optimization control."""
        return {
            'use_low_cpu_mem': os.environ.get("ENABLE_LOW_CPU_MEM", "true").lower() == "true",
            'use_attention_slicing': os.environ.get("ENABLE_ATTENTION_SLICING", "true").lower() == "true",
            'use_vae_slicing': os.environ.get("ENABLE_VAE_SLICING", "true").lower() == "true",
            'use_cpu_offload': os.environ.get("ENABLE_CPU_OFFLOAD", "true").lower() == "true"
        }
    
    def _detect_device(self):
        """Determine the best available device."""
        if torch.cuda.is_available():
            return torch.device("cuda"), "cuda"
        elif torch.backends.mps.is_available():
            return torch.device("mps"), "mps"
        else:
            return torch.device("cpu"), "cpu"
    
    def _check_bfloat16_support(self):
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
    
    def _get_model_native_dtype(self):
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
    
    def _intelligent_dtype_selection(self, device_type):
        """Automatically select the best dtype based on hardware and model."""
        if device_type == "cuda":
            # Priority: bfloat16 -> model native -> float16 -> float32
            if self._check_bfloat16_support():
                print("DTYPE=auto: Selected bfloat16 (hardware optimal)")
                return torch.bfloat16
            
            model_native = self._get_model_native_dtype()
            if model_native != torch.float32:
                print(f"DTYPE=auto: Selected {model_native} (model native)")
                return model_native
            
            print("DTYPE=auto: Selected float16 (CUDA fallback)")
            return torch.float16
            
        elif device_type == "mps":
            # MPS: model native -> float32 (avoid float16 instability)
            model_native = self._get_model_native_dtype()
            if model_native == torch.float32:
                print("DTYPE=auto: Selected float32 (MPS stable)")
                return torch.float32
            else:
                print(f"DTYPE=auto: Selected float32 (MPS override from {model_native})")
                return torch.float32
                
        else:  # CPU
            # CPU: model native -> float32
            model_native = self._get_model_native_dtype()
            print(f"DTYPE=auto: Selected {model_native} (CPU)")
            return model_native
    
    def _get_dtype_with_fallback(self, target_dtype, device_type):
        """Get target dtype with intelligent fallback if unsupported."""
        if target_dtype == torch.bfloat16:
            if device_type == "cuda" and self._check_bfloat16_support():
                print(f"DTYPE=bfloat16: Using bfloat16")
                return torch.bfloat16
            else:
                print(f"DTYPE=bfloat16: Hardware unsupported, falling back")
                # Fallback chain: model native -> float16 -> float32
                model_native = self._get_model_native_dtype()
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
                model_native = self._get_model_native_dtype()
                print(f"DTYPE=float16: Fallback to {model_native}")
                return model_native
                
        else:  # target_dtype == torch.float32 or other
            return target_dtype
    
    def _determine_torch_dtype(self, device_type):
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
            model_native = self._get_model_native_dtype()
            print(f"DTYPE=native: Using {model_native}")
            return model_native
        else:  # "auto" or invalid value
            return self._intelligent_dtype_selection(device_type)
    
    def _load_pipeline(self, config, device, torch_dtype):
        """Load the diffusion pipeline with appropriate optimizations."""
        if config['use_low_cpu_mem'] or torch_dtype != torch.float32:
            pipeline = DiffusionPipeline.from_pretrained(
                self.model_id,
                low_cpu_mem_usage=config['use_low_cpu_mem'],
                torch_dtype=torch_dtype
            )
        else:
            pipeline = DiffusionPipeline.from_pretrained(self.model_id)
        
        pipeline.to(device)
        return pipeline
    
    def _apply_optimizations(self, pipeline, device_type, config):
        """Apply device-specific optimizations to the pipeline."""
        if device_type == "cuda":
            self._apply_cuda_optimizations(pipeline, config)
        elif device_type == "mps":
            self._apply_mps_optimizations(pipeline, config)
        # CPU doesn't need special optimizations for basic inference
    
    def _apply_cuda_optimizations(self, pipeline, config):
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
    
    def _apply_mps_optimizations(self, pipeline, config):
        """Apply MPS-specific optimizations."""
        if config['use_attention_slicing'] and hasattr(pipeline, 'enable_attention_slicing'):
            pipeline.enable_attention_slicing()
            print("Enabled attention slicing (MPS)")
        
        # Additional MPS memory optimizations (use with caution)
        if config['use_vae_slicing'] and hasattr(pipeline, 'enable_vae_slicing'):
            pipeline.enable_vae_slicing()
            print("Enabled VAE slicing (MPS)")
    
    def load(self):
        """Load the diffusion pipeline with configurable optimizations."""
        config = self._parse_optimization_flags()
        device, device_type = self._detect_device()
        torch_dtype = self._determine_torch_dtype(device_type)
        
        print(f"Using device: {device}")
        print(f"Selected dtype: {torch_dtype}")
        print(f"Optimizations: {config}")
        
        pipeline = self._load_pipeline(config, device, torch_dtype)
        self._apply_optimizations(pipeline, device_type, config)
        
        self.pipeline = pipeline
        # The ready flag is used by model ready endpoint for readiness probes,
        # set to True when model is loaded successfully without exceptions.
        self.ready = True

    def preprocess(
            self, payload: Union[Dict, InferRequest], headers: Dict[str, str] = None
    ) -> Dict:
        if isinstance(payload, Dict) and "instances" in payload:
            headers["request-type"] = "v1"
        elif isinstance(payload, InferRequest):
            raise InvalidInput("v2 protocol not implemented")
        else:
            raise InvalidInput("invalid payload")

        return payload["instances"][0]

    def predict(
            self, payload: Union[Dict, InferRequest], headers: Dict[str, str] = None
    ) -> Union[Dict, InferResponse]:
        try:
            # Validate required parameters
            if "prompt" not in payload:
                raise InvalidInput("Missing required parameter: prompt")
            
            # Generate image using the pipeline
            image = self.pipeline(**payload).images[0]
            
            # Convert image to base64
            image_bytes = io.BytesIO()
            image.save(image_bytes, format='PNG')
            image_bytes.seek(0)

            # Encode as base64 string (not bytes)
            im_b64 = base64.b64encode(image_bytes.read()).decode('utf-8')

            return {
                "predictions": [
                    {
                        "model_name": self.model_id,
                        "prompt": payload["prompt"],
                        "image": {
                            "format": "PNG",
                            "b64": im_b64
                        }
                    }
                ]
            }
        except Exception as e:
            # Log the error for debugging
            print(f"Prediction error: {str(e)}")
            raise InvalidInput(f"Prediction failed: {str(e)}")


parser = argparse.ArgumentParser(parents=[model_server.parser])
args, _ = parser.parse_known_args()

if __name__ == "__main__":
    model = DiffusersModel(args.model_name)
    model.load()
    ModelServer().start([model])