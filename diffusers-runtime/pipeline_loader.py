"""
Pipeline loading and configuration for diffusion models.
"""
import torch
from typing import Dict
from diffusers import DiffusionPipeline


class PipelineLoader:
    """Handles loading and initial configuration of diffusion pipelines."""
    
    def __init__(self, model_id: str):
        self.model_id = model_id
    
    def load_pipeline(self, device: torch.device, torch_dtype: torch.dtype, 
                     config: Dict[str, bool]) -> DiffusionPipeline:
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