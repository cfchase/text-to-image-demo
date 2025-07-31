CONTAINER_RUNTIME ?= podman

build:
	$(CONTAINER_RUNTIME) build --platform linux/amd64 -t quay.io/cfchase/diffusers-runtime:latest -f docker/Dockerfile .

push:
	$(CONTAINER_RUNTIME) tag quay.io/cfchase/diffusers-runtime:latest quay.io/cfchase/diffusers-runtime:v0.2
	$(CONTAINER_RUNTIME) push quay.io/cfchase/diffusers-runtime:latest
	$(CONTAINER_RUNTIME) push quay.io/cfchase/diffusers-runtime:v0.2

run:
	$(CONTAINER_RUNTIME) run -ePORT=8080 -p8080:8080 quay.io/cfchase/diffusers-runtime:latest

deploy:
	oc apply -f templates/inference-service.yaml

undeploy:
	oc delete -f templates/route.yaml
	oc delete -f templates/inference-service.yaml

test-v1:
	curl -H "Content-Type: application/json" localhost:8080/v1/models/model:predict -d @./scripts/v1_input.json | jq -r '.predictions[0].image.b64' | base64 -d > "example_output.png"
