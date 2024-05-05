#!/usr/bin/env bash

oc apply -f ./setup/rhoai-config/images-puller.yaml
oc apply -f ./setup/rhoai-config/template-modelmesh-triton.yaml


oc apply -f ./setup/image-gen/ds-project.yaml
while ! kubectl get namespace image-generation -o jsonpath='{.status.phase}' | grep -q Active; do
    echo "Waiting for the pod to complete. Press CTRL-C to exit."
    sleep 1
done

oc apply -n image-generation -f ./setup/image-gen/setup-s3.yaml
oc wait -n image-generation --for=condition=Complete job/create-minio-buckets

#oc apply -n image-generation -f ./setup/image-gen/dspa.yaml
#oc apply -n image-generation -f ./setup/image-gen/create-ds-pipeline-config.yaml
#oc wait -n image-generation --for=condition=Complete job/create-ds-pipeline-config

