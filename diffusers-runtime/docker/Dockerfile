FROM registry.access.redhat.com/ubi9/python-311:1-1753713955

# By default, listen on port 8080
EXPOSE 8080/tcp
ENV FLASK_PORT=8080

# Set the working directory in the container
WORKDIR /projects

# Copy the content of the local src directory to the working directory
COPY . .

# Install base dependencies first (including PyTorch)
RUN pip install -r requirements-base.txt

# Install GPU dependencies that require PyTorch (like flash-attn)
# Use --no-build-isolation so flash-attn can see the installed torch
RUN pip install --no-build-isolation -r requirements-gpu.txt

# Specify the command to run on container start
ENTRYPOINT ["python", "./model.py"]
