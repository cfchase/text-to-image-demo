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

    def load(self):
        # Load pipeline with memory optimizations using accelerate
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load with low memory usage for better memory efficiency
        pipeline = DiffusionPipeline.from_pretrained(
            self.model_id,
            low_cpu_mem_usage=True,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )
        
        # Move to device
        pipeline.to(device)
        
        # Apply GPU-specific memory optimizations
        if torch.cuda.is_available():
            # Check which optimizations are available for this pipeline type
            
            # Enable attention slicing if available (most pipelines support this)
            if hasattr(pipeline, 'enable_attention_slicing'):
                pipeline.enable_attention_slicing()
            
            # Enable VAE slicing if available (SD 1.x/2.x/XL support this, SD3 may not)
            if hasattr(pipeline, 'enable_vae_slicing'):
                pipeline.enable_vae_slicing()
            
            # Use accelerate's CPU offload for better memory management
            if hasattr(pipeline, 'enable_model_cpu_offload'):
                pipeline.enable_model_cpu_offload()
            # Enable sequential CPU offload as fallback (older method, more compatible)
            elif hasattr(pipeline, 'enable_sequential_cpu_offload'):
                pipeline.enable_sequential_cpu_offload()
            
            # Note: SD 3.5 has built-in memory optimizations, fewer manual optimizations needed
        
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
        image = self.pipeline(**payload).images[0]
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG')
        image_bytes.seek(0)

        im_b64 = base64.b64encode(image_bytes.read())

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
            ]}


parser = argparse.ArgumentParser(parents=[model_server.parser])
args, _ = parser.parse_known_args()

if __name__ == "__main__":
    model = DiffusersModel(args.model_name)
    model.load()
    ModelServer().start([model])
