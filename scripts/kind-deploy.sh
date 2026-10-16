#!/bin/bash
# SafeCity Kind Cluster Deployment Script
# Free local Kubernetes demo ($0 cost)
# Demonstrates Helm chart deployment and CI/CD pipeline end-to-end

set -e

echo "=== SafeCity Kind Cluster Setup ==="
echo ""

# Step 1: Create Kind cluster
echo "1. Creating Kind cluster..."
kind create cluster --name safecity
echo "   Kind cluster created"

# Step 2: Install metrics-server (required for HPA)
echo ""
echo "2. Installing metrics-server..."
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
# Patch for kind (insecure TLS for development)
kubectl patch deployment metrics-server -n kube-system --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
echo "   metrics-server installed"

# Step 3: Add Helm repo and install chart dependencies
echo ""
echo "3. Adding Helm repository..."
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
echo "   Helm repository updated"

echo ""
echo "4. Installing PostgreSQL..."
helm install pg bitnami/postgresql \
  --set auth.database=safecity,auth.username=safecity,auth.password=safecity \
  --namespace safecity-dev --create-namespace
echo "   PostgreSQL deployed"

echo ""
echo "5. Installing Redis..."
helm install redis bitnami/redis --set auth.enabled=false \
  --namespace safecity-dev
echo "   Redis deployed"

echo ""
echo "6. Building Docker images..."
docker build -t safecity-backend:1.0.0 ./backend
docker build -t safecity-frontend:1.0.0 ./frontend
kind load docker-image safecity-backend:1.0.0 --name safecity
kind load docker-image safecity-frontend:1.0.0 --name safecity
echo "   Docker images built and loaded"

echo ""
echo "7. Deploying Helm chart..."
helm upgrade --install safecity infrastructure/helm/safecity \
  --namespace safecity-dev --create-namespace \
  -f infrastructure/helm/safecity/values-kind.yaml \
  --set secret.secretKey=dev-only-not-a-real-secret \
  --set secret.postgresPassword=safecity
echo "   Helm chart deployed"

# Step 8: Seed demo data
echo ""
echo "8. Seeding demo data..."
kubectl exec -n safecity-dev deployment/safecity-backend -- python manage.py seed_demo_data
echo "   Demo data seeded"

# Step 9: Verify deployment
echo ""
echo "9. Verifying deployment..."
echo "   Pod status:"
kubectl get pods -n safecity-dev
echo ""
echo "   Services:"
kubectl get services -n safecity-dev
echo ""
echo "   HPA status:"
kubectl get hpa -n safecity-dev

echo ""
echo "10. Running Helm validation..."
helm lint infrastructure/helm/safecity -f infrastructure/helm/safecity/values-kind.yaml
echo "   Helm lint passed"

echo ""
echo "=== Kind Cluster Setup Complete ==="
echo "Access the application:"
echo "  kubectl port-forward -n safecity-dev service/safecity-frontend 5174:80"
echo "  Then open: http://localhost:5174"
echo ""
echo "Teardown: kind delete cluster --name safecity"