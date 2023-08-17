# Stable Diffusion and Dreambooth on RHODS


## Requirements
The notebooks can be run as is on the RHODS PyTorch notebook.

This demo requires a gpu with at least 24GB of memory.  It also requires 2 buckets of S3 compatible storage.


## Setup
1. Create a data science project
2. Open the OpenShift console
3. Navigate to the created OpenShift project
4. Import setup/setup-s3.yaml
5. Create a pipeline server using the `Pipeline Artifacts` data connection.
6. Create a notebook using the PyTorch RHODS image and using the `My Storage` data connection
7. Clone this repo (`https://github.com/cfchase/text-to-image-demo.git`)
