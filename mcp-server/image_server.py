#!/usr/bin/env python3
"""Simple HTTP server for serving generated images"""

import os
import argparse
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial


class ImageHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP request handler that only serves image files"""
    
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)
    
    def end_headers(self):
        # Add CORS headers for browser access
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        super().end_headers()
    
    def do_GET(self):
        # Only serve files, not directory listings
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            self.send_error(403, "Directory listing not allowed")
            return
        
        # Only serve image files
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
        if not any(path.endswith(ext) for ext in allowed_extensions):
            self.send_error(403, "Only image files are allowed")
            return
        
        super().do_GET()


def run_server(port: int, directory: str):
    """Run the image HTTP server"""
    # Ensure directory exists
    Path(directory).mkdir(parents=True, exist_ok=True)
    
    handler_class = partial(ImageHTTPRequestHandler, directory=directory)
    server = HTTPServer(('', port), handler_class)
    
    print(f"Serving images from {directory} on http://localhost:{port}")
    print(f"Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Serve generated images via HTTP")
    parser.add_argument(
        "--port", 
        type=int, 
        default=8001, 
        help="Port to serve on (default: 8001)"
    )
    parser.add_argument(
        "--directory", 
        type=str, 
        default=os.environ.get("IMAGE_OUTPUT_PATH", "/tmp/image-generator"),
        help="Directory to serve images from (default: IMAGE_OUTPUT_PATH or /tmp/image-generator)"
    )
    
    args = parser.parse_args()
    run_server(args.port, args.directory)


if __name__ == "__main__":
    main()