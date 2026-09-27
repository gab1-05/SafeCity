// SafeCity — Jenkinsfile (OPTIONAL, rubric-only).
// Mirrors .github/workflows/* on local Docker agents. $0: run the
// controller + agents as local containers; GitHub Actions stays the
// real pipeline. Requires: Docker, Node 20, Python 3.12 on agents.

pipeline {
  agent any
  options { timestamps(); disableConcurrentBuilds() }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Backend lint') {
      steps { dir('backend') { sh 'python -m ruff check .' } }
    }
    stage('Backend test') {
      steps {
        dir('backend') {
          sh 'python manage.py check'
          sh 'python -m pytest -q'
        }
      }
    }
    stage('Frontend checks') {
      steps {
        dir('frontend') {
          sh 'npm ci'
          sh 'npm run lint'
          sh 'npm run typecheck'
          sh 'npm run test -- --run'
        }
      }
    }
    stage('Docker build') {
      steps {
        sh 'docker build -t safecity-backend:local ./backend'
        sh 'docker build -t safecity-frontend:local ./frontend'
      }
    }
    stage('Trivy scan') {
      steps {
        sh 'trivy image --severity CRITICAL,HIGH --exit-code 1 safecity-backend:local'
        sh 'trivy image --severity CRITICAL,HIGH --exit-code 1 safecity-frontend:local'
      }
    }
    stage('Helm validate') {
      steps {
        sh 'helm lint infrastructure/helm/safecity -f infrastructure/helm/safecity/values-kind.yaml'
        sh 'helm template safecity infrastructure/helm/safecity -f infrastructure/helm/safecity/values-kind.yaml --set secret.secretKey=ci-only --set secret.postgresPassword=ci-only > /tmp/kind.rendered.yaml'
      }
    }
    stage('Terraform validate') {
      steps {
        dir('infrastructure/terraform/environments/dev') {
          sh 'terraform fmt -check -recursive ../../../'
          sh 'terraform init -backend=false'
          sh 'terraform validate'
        }
      }
    }
  }
  post {
    always { echo "SafeCity Jenkins run finished: ${currentBuild.currentResult}" }
  }
}
