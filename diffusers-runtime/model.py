import os
import io
import base64
import argparse

from typing import Dict, Union
import torch
from accelerate import init_empty_weights, load_checkpoint_and_dispatch

from kserve import (
    Model,
    ModelServer,
    model_server,
    InferRequest,
    InferResponse,
)
from kserve.errors import InvalidInput

from device_manager import DeviceManager
from dtype_selector import DtypeSelector
from optimization_manager import OptimizationManager
from pipeline_loader import PipelineLoader


class DiffusersModel(Model):
    def __init__(self, name: str):
        super().__init__(name)
        self.model_id = os.environ.get("MODEL_ID", default="/mnt/models")
        self.pipeline = None
        self.refiner = None
        self.ready = False
        
        # Initialize component managers
        self.device_manager = DeviceManager()
        self.dtype_selector = DtypeSelector(self.model_id, self.device_manager)
        self.optimization_manager = OptimizationManager()
        self.pipeline_loader = PipelineLoader(self.model_id)
        
        self.load()

    
    def load(self):
        """Load the diffusion pipeline with configurable optimizations."""
        config = self.optimization_manager.parse_optimization_flags()
        device, device_type = self.device_manager.detect_device()
        torch_dtype = self.dtype_selector.determine_torch_dtype(device_type)
        
        print(f"Using device: {device}")
        print(f"Selected dtype: {torch_dtype}")
        print(f"Optimizations: {config}")
        
        pipeline = self.pipeline_loader.load_pipeline(device, torch_dtype, config)
        self.optimization_manager.apply_optimizations(pipeline, device_type, config)
        
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