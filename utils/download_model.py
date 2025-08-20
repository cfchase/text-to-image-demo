#!/usr/bin/env python3
"""
Download a HuggingFace model to a local directory.

Usage:
    python download_model.py <model_id> <output_dir>
    
Example:
    python download_model.py stabilityai/stable-diffusion-3.5-medium ./models/sd3.5
    python download_model.py segmind/tiny-sd ./models/tiny-sd
"""

import os
import sys
import argparse
from pathlib import Path
from huggingface_hub import snapshot_download


def download_model(model_id: str, output_dir: str, use_auth_token: bool = False):
    """
    Download model weights from HuggingFace Hub.
    
    Args:
        model_id: HuggingFace model ID
        output_dir: Directory to save the model
        use_auth_token: Whether to use HuggingFace authentication token
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading model: {model_id}")
    print(f"Output directory: {output_path.absolute()}")
    
    try:
        snapshot_path = snapshot_download(
            repo_id=model_id,
            local_dir=str(output_path),
            local_dir_use_symlinks=False,
            use_auth_token=use_auth_token
        )
        print(f"✓ Successfully downloaded model to {snapshot_path}")
        
        # List downloaded files
        files = list(output_path.rglob("*"))
        print(f"\nDownloaded {len([f for f in files if f.is_file()])} files:")
        for f in sorted([f for f in files if f.is_file()])[:10]:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  - {f.relative_to(output_path)} ({size_mb:.1f} MB)")
        if len([f for f in files if f.is_file()]) > 10:
            print(f"  ... and {len([f for f in files if f.is_file()]) - 10} more files")
            
    except Exception as e:
        print(f"✗ Failed to download model: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Download model weights from HuggingFace Hub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download Stable Diffusion model
  python download_model.py stabilityai/stable-diffusion-3.5-medium ./models/sd3.5
  
  # Download small test model
  python download_model.py segmind/tiny-sd ./models/tiny-sd
  
  # Download with authentication (for gated models)
  python download_model.py --auth stabilityai/stable-diffusion-3.5-large ./models/sd3.5-large
        """
    )
    
    parser.add_argument("model_id", help="HuggingFace model ID (e.g., 'stabilityai/stable-diffusion-3.5-medium')")
    parser.add_argument("output_dir", help="Directory to save the model")
    parser.add_argument("--auth", action="store_true",
                        help="Use HuggingFace authentication token (reads from HF_TOKEN env var or ~/.huggingface/token)")
    
    args = parser.parse_args()
    
    # Check for HF token if auth is requested
    use_auth = False
    if args.auth:
        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        if not token:
            token_file = Path.home() / ".huggingface" / "token"
            if token_file.exists():
                token = token_file.read_text().strip()
                use_auth = True
        else:
            use_auth = True
        
        if not use_auth:
            print("Warning: --auth specified but no token found. Set HF_TOKEN environment variable or login with 'huggingface-cli login'")
    
    # Download the model
    download_model(args.model_id, args.output_dir, use_auth)


if __name__ == "__main__":
    main()