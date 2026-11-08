.PHONY: help up down train test lint clean

PYTHON ?= python

help:
	@echo "Available commands:"
	@echo "  make up               - Create k3d cluster, build image, and deploy all manifests"
	@echo "  make down             - Delete k3d cluster and clean up resources"
	@echo "  make train            - Train student model using config.yaml"
	@echo "  make train SUBSET=50  - Train student model on first 50 records"
	@echo "  make test             - Run unit tests"
	@echo "  make score            - Evaluate predictions against validation set"
	@echo "  make clean            - Clean temporary files and caches"

up:
	k3d cluster create --config cluster/k3d.yaml
	docker build -t parser-service:v1 -f service/Dockerfile . && k3d image import parser-service:v1 -c cloud-cluster
	kubectl apply -f k8s/namespaces.yaml -f k8s/secret.yaml -f k8s/seaweedfs.yaml -f k8s/deployment.yaml -f k8s/service.yaml -f k8s/ingress.yaml -f k8s/hpa.yaml

down:
	k3d cluster delete cloud-cluster

train:
ifdef SUBSET
	$(PYTHON) training/train.py --subset $(SUBSET)
else
	$(PYTHON) training/train.py
endif

test:
	$(PYTHON) -m unittest discover -s tests -p "test_*.py"

score:
	$(PYTHON) tools/score.py results/predictions_student.jsonl data/validation.jsonl --min-validity 95

clean:
	rm -rf __pycache__ */__pycache__ *.pyc

