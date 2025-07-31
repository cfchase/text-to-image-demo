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
            'use_float16': os.environ.get("ENABLE_FLOAT16", "true").lower() == "true",
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
    
    def _determine_torch_dtype(self, device_type, use_float16):
        """Determine the appropriate torch dtype based on device and user preference."""
        if not use_float16:
            return torch.float32
        
        if device_type == "cuda":
            return torch.float16
        elif device_type == "mps":
            # MPS can be unstable with float16, keep float32 by default
            return torch.float32
        else:
            return torch.float32
    
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
        torch_dtype = self._determine_torch_dtype(device_type, config['use_float16'])
        
        print(f"Using device: {device}")
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