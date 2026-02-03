# Infrastructure as Code (IaC) Planning

## Overview
This document defines the Infrastructure as Code (IaC) strategy for the Senzu AI system. IaC enables version-controlled, reproducible, and automated infrastructure provisioning, supporting rapid deployment, disaster recovery, and multi-environment management.

---

## IaC Technology Stack

### Primary Tools

| Tool | Purpose | Use Case |
|------|---------|----------|
| **Terraform** | Infrastructure provisioning | AWS resources (VPC, RDS, S3, ECS, etc.) |
| **Docker** | Containerization | Application packaging |
| **Kubernetes** | Container orchestration | Service deployment, scaling, management |
| **Helm** | Kubernetes package manager | Application templates, versioning |
| **GitHub Actions** | CI/CD automation | Build, test, deploy pipeline |

### Alternative: Serverless-First Approach

| Tool | Purpose | Use Case |
|------|---------|----------|
| **AWS CDK** | Infrastructure as code | Define AWS resources in Python/TypeScript |
| **Serverless Framework** | Serverless deployment | Lambda functions, API Gateway |
| **Docker** | Containerization | For services not suited to Lambda |

**Decision**: Recommend **Terraform + Kubernetes** for flexibility and vendor-agnostic approach.

---

## Infrastructure Architecture

### Cloud Provider: AWS (Recommended)

**Rationale**:
- Mature managed services (RDS, ElastiCache, S3)
- Strong ML/AI ecosystem (SageMaker, Lambda)
- Cost-effective for startups (free tier, credits)
- Extensive Terraform support

**Alternatives**: GCP (good ML tools), Azure (enterprise focus)

### Multi-Environment Strategy

| Environment | Purpose | Infrastructure Scale | Cost |
|-------------|---------|---------------------|------|
| **Development** | Local development | Minimal (single instance per service) | Low |
| **Staging** | Pre-production testing | Medium (2 instances per service) | Medium |
| **Production** | Live user traffic | High (auto-scaling, 3+ instances) | High |

**Isolation**:
- Separate AWS accounts per environment (or separate VPCs)
- Separate databases per environment
- Shared S3 bucket (with environment prefixes: `prod/`, `staging/`)

---

## Terraform Configuration

### Directory Structure

```
infrastructure/
├── terraform/
│   ├── modules/
│   │   ├── vpc/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── rds/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── redis/
│   │   ├── s3/
│   │   ├── ecs/
│   │   └── eks/
│   ├── environments/
│   │   ├── dev/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── terraform.tfvars
│   │   ├── staging/
│   │   └── prod/
│   ├── backend.tf         # Terraform state backend (S3)
│   └── provider.tf        # AWS provider configuration
├── kubernetes/
│   ├── base/              # Kustomize base configs
│   ├── overlays/          # Environment-specific overlays
│   └── helm-charts/       # Custom Helm charts
├── docker/
│   ├── api-gateway/
│   │   └── Dockerfile
│   ├── inference-service/
│   │   └── Dockerfile
│   └── ...
└── scripts/
    ├── deploy.sh
    └── rollback.sh
```

### Terraform Modules

#### Module: VPC

**Resources Created**:
- VPC with CIDR block `10.0.0.0/16`
- 3 public subnets (for load balancers)
- 3 private subnets (for services)
- 3 data subnets (for databases)
- Internet Gateway
- NAT Gateways (for private subnet outbound)
- Route tables
- Security groups

**variables.tf**:
```hcl
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "AWS availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}
```

#### Module: RDS (PostgreSQL)

**Resources Created**:
- RDS PostgreSQL instance (or Aurora Serverless)
- DB subnet group
- Security group (allow port 5432 from app subnet)
- Automated backups (daily snapshots)
- Read replicas (production only)

**variables.tf**:
```hcl
variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 100
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = false
}

variable "backup_retention_period" {
  description = "Backup retention in days"
  type        = number
  default     = 7
}
```

**main.tf**:
```hcl
resource "aws_db_instance" "postgresql" {
  identifier             = "senzu-ai-${var.environment}"
  engine                 = "postgres"
  engine_version         = "14.7"
  instance_class         = var.instance_class
  allocated_storage      = var.allocated_storage
  storage_type           = "gp3"
  storage_encrypted      = true
  kms_key_id             = aws_kms_key.rds.arn

  db_name                = "senzu_ai"
  username               = "senzu_admin"
  password               = random_password.db_password.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = var.backup_retention_period
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  multi_az               = var.multi_az
  publicly_accessible    = false

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
```

#### Module: ElastiCache (Redis)

**Resources Created**:
- ElastiCache Redis cluster (3 nodes)
- Subnet group
- Security group
- Parameter group (custom Redis config)

**main.tf**:
```hcl
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "senzu-ai-${var.environment}"
  replication_group_description = "Redis cluster for Senzu AI"

  engine                     = "redis"
  engine_version             = "7.0"
  node_type                  = var.node_type
  num_cache_clusters         = var.num_cache_clusters
  parameter_group_name       = aws_elasticache_parameter_group.redis.name

  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token_enabled         = true
  auth_token                 = random_password.redis_token.result

  automatic_failover_enabled = true
  multi_az_enabled           = var.multi_az

  snapshot_retention_limit   = 5
  snapshot_window            = "03:00-05:00"

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
```

#### Module: S3 Buckets

**Resources Created**:
- Model artifacts bucket
- Feature data lake bucket
- Backups bucket
- Bucket policies (restrict access)
- Lifecycle policies (archive to Glacier)

**main.tf**:
```hcl
resource "aws_s3_bucket" "models" {
  bucket = "senzu-ai-models-${var.environment}"

  tags = {
    Environment = var.environment
    Purpose     = "Model Artifacts"
  }
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    id     = "archive-old-versions"
    status = "Enabled"

    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}
```

#### Module: EKS (Elastic Kubernetes Service)

**Resources Created**:
- EKS cluster
- Node groups (auto-scaling)
- IAM roles (cluster, node group)
- OIDC provider (for IAM roles for service accounts)

**main.tf**:
```hcl
resource "aws_eks_cluster" "main" {
  name     = "senzu-ai-${var.environment}"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.27"

  vpc_config {
    subnet_ids              = var.private_subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.allowed_cidr_blocks
    security_group_ids      = [aws_security_group.eks_cluster.id]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  tags = {
    Environment = var.environment
  }
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "senzu-ai-nodes-${var.environment}"
  node_role_arn   = aws_iam_role.eks_nodes.arn
  subnet_ids      = var.private_subnet_ids

  scaling_config {
    desired_size = var.desired_size
    max_size     = var.max_size
    min_size     = var.min_size
  }

  instance_types = [var.instance_type]

  tags = {
    Environment = var.environment
  }
}
```

---

## Kubernetes Configuration

### Deployment Strategy: Helm Charts

**Why Helm**:
- Templating for environment-specific configs
- Version management (rollback support)
- Package sharing (Helm repository)

### Directory Structure

```
kubernetes/
├── helm-charts/
│   ├── api-gateway/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   ├── values-dev.yaml
│   │   ├── values-prod.yaml
│   │   └── templates/
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       ├── ingress.yaml
│   │       ├── configmap.yaml
│   │       └── secret.yaml
│   ├── inference-service/
│   ├── feature-service/
│   └── ...
└── base/
    ├── namespace.yaml
    └── rbac.yaml
```

### Example: Helm Chart for Inference Service

**Chart.yaml**:
```yaml
apiVersion: v2
name: inference-service
description: Senzu AI Inference Service
version: 1.0.0
appVersion: "1.0.0"
```

**values.yaml** (defaults):
```yaml
replicaCount: 2

image:
  repository: senzu-ai/inference-service
  tag: "latest"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8080

resources:
  limits:
    cpu: 1000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: database-credentials
        key: url
  - name: REDIS_URL
    valueFrom:
      secretKeyRef:
        name: redis-credentials
        key: url
  - name: LOG_LEVEL
    value: "INFO"
```

**values-prod.yaml** (production overrides):
```yaml
replicaCount: 5

image:
  tag: "v1.2.3"  # Specific version tag

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 1000m
    memory: 2Gi

autoscaling:
  minReplicas: 5
  maxReplicas: 20

env:
  - name: LOG_LEVEL
    value: "WARN"
```

**templates/deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "inference-service.fullname" . }}
  labels:
    app: {{ include "inference-service.name" . }}
    version: {{ .Values.image.tag }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ include "inference-service.name" . }}
  template:
    metadata:
      labels:
        app: {{ include "inference-service.name" . }}
        version: {{ .Values.image.tag }}
    spec:
      containers:
      - name: inference-service
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        ports:
        - containerPort: {{ .Values.service.port }}
        env:
        {{- range .Values.env }}
        - name: {{ .name }}
          {{- if .value }}
          value: {{ .value | quote }}
          {{- else if .valueFrom }}
          valueFrom:
            {{- toYaml .valueFrom | nindent 12 }}
          {{- end }}
        {{- end }}
        resources:
          {{- toYaml .Values.resources | nindent 12 }}
        livenessProbe:
          httpGet:
            path: /health/live
            port: {{ .Values.service.port }}
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: {{ .Values.service.port }}
          initialDelaySeconds: 10
          periodSeconds: 5
```

**templates/service.yaml**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "inference-service.fullname" . }}
spec:
  type: {{ .Values.service.type }}
  ports:
  - port: {{ .Values.service.port }}
    targetPort: {{ .Values.service.port }}
    protocol: TCP
    name: http
  selector:
    app: {{ include "inference-service.name" . }}
```

**templates/hpa.yaml** (Horizontal Pod Autoscaler):
```yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "inference-service.fullname" . }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "inference-service.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
```

---

## Docker Configuration

### Multi-Stage Dockerfile (Python Service)

**docker/inference-service/Dockerfile**:
```dockerfile
# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY src/ ./src/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Docker Compose (Local Development)

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: senzu_ai_dev
      POSTGRES_USER: senzu
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  api-gateway:
    build:
      context: ./services/api-gateway
      dockerfile: Dockerfile
    ports:
      - "8000:8080"
    environment:
      DATABASE_URL: postgresql://senzu:dev_password@postgres:5432/senzu_ai_dev
      REDIS_URL: redis://redis:6379
      LOG_LEVEL: DEBUG
    depends_on:
      - postgres
      - redis

  inference-service:
    build:
      context: ./services/inference-service
      dockerfile: Dockerfile
    ports:
      - "8001:8080"
    environment:
      DATABASE_URL: postgresql://senzu:dev_password@postgres:5432/senzu_ai_dev
      REDIS_URL: redis://redis:6379
      LOG_LEVEL: DEBUG
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
  redis_data:
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

**.github/workflows/deploy.yml**:
```yaml
name: Deploy to Production

on:
  push:
    branches:
      - main
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: senzu-ai/inference-service
  EKS_CLUSTER_NAME: senzu-ai-prod

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: pytest --cov=src tests/

      - name: Lint
        run: |
          pip install flake8 black mypy
          flake8 src/
          black --check src/
          mypy src/

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Build, tag, and push image to Amazon ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig --name ${{ env.EKS_CLUSTER_NAME }} --region ${{ env.AWS_REGION }}

      - name: Install Helm
        uses: azure/setup-helm@v3
        with:
          version: '3.12.0'

      - name: Deploy with Helm
        run: |
          helm upgrade --install inference-service ./kubernetes/helm-charts/inference-service \
            --namespace production \
            --values ./kubernetes/helm-charts/inference-service/values-prod.yaml \
            --set image.tag=${{ github.sha }} \
            --wait \
            --timeout 5m

      - name: Verify deployment
        run: |
          kubectl rollout status deployment/inference-service -n production
          kubectl get pods -n production -l app=inference-service
```

### Deployment Strategies

#### 1. Rolling Update (Default)

**Strategy**:
- Deploy new version gradually
- Replace old pods one-by-one
- Zero downtime

**Configuration**:
```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Max new pods during update
      maxUnavailable: 0  # Min pods available during update
```

#### 2. Blue-Green Deployment

**Strategy**:
- Deploy new version alongside old version
- Switch traffic once new version validated
- Instant rollback possible

**Implementation**: Use Kubernetes Services with label selectors

#### 3. Canary Deployment

**Strategy**:
- Deploy new version to small % of traffic (e.g., 10%)
- Monitor metrics (error rate, latency)
- Gradually increase traffic if stable
- Rollback if issues detected

**Implementation**: Use Istio or Flagger for traffic splitting

---

## Secrets Management

### External Secrets Operator

**Why**: Sync secrets from AWS Secrets Manager to Kubernetes

**Installation**:
```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n kube-system
```

**ExternalSecret Resource**:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: database-credentials
    creationPolicy: Owner
  data:
  - secretKey: url
    remoteRef:
      key: senzu-ai/prod/database-url
```

---

## Monitoring & Logging

### Prometheus + Grafana

**Installation**:
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring
```

**ServiceMonitor** (scrape metrics from service):
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: inference-service
  namespace: production
spec:
  selector:
    matchLabels:
      app: inference-service
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### Centralized Logging (ELK or Loki)

**Option 1: ELK Stack** (Elasticsearch, Logstash, Kibana)
**Option 2: Loki** (Grafana Loki - lightweight)

**Recommendation**: Loki (easier to manage, integrates with Grafana)

**Installation**:
```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack -n monitoring
```

---

## Disaster Recovery

### Backup Strategy

| Component | Backup Frequency | Retention | Storage |
|-----------|------------------|-----------|---------|
| PostgreSQL | Daily (automated snapshots) | 30 days | AWS RDS Backups |
| Redis | Daily (RDB snapshots) | 7 days | S3 |
| S3 (models) | Versioning enabled | 90 days | S3 Glacier |
| Kubernetes configs | On every change | Indefinite | Git repository |

### Recovery Procedures

#### Database Restore

```bash
# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier senzu-ai-restored \
  --db-snapshot-identifier rds:senzu-ai-prod-2025-10-15

# Update DNS/connection string to point to restored instance
```

#### Kubernetes Disaster Recovery

```bash
# Re-apply all infrastructure (Terraform)
cd infrastructure/terraform/environments/prod
terraform apply

# Redeploy services (Helm)
helm upgrade --install inference-service ./kubernetes/helm-charts/inference-service \
  --namespace production \
  --values ./kubernetes/helm-charts/inference-service/values-prod.yaml
```

### Multi-Region Disaster Recovery (Future)

**Strategy**:
- Primary region: `us-east-1`
- Failover region: `us-west-2`
- Database replication: Cross-region read replicas
- S3 replication: Cross-region replication enabled
- DNS failover: Route 53 health checks + failover routing

---

## Cost Optimization

### Strategies

1. **Auto-Scaling**: Scale down during low-traffic hours
2. **Spot Instances**: Use spot instances for non-critical workloads (70% cost savings)
3. **Reserved Instances**: Purchase 1-year/3-year reserved instances for baseline capacity
4. **S3 Lifecycle Policies**: Archive old data to Glacier
5. **Right-Sizing**: Monitor resource usage, downsize over-provisioned instances

### Estimated Monthly Costs (Production)

| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| EKS Cluster | Control plane | $72 |
| EC2 Instances (EKS nodes) | 5x t3.xlarge (on-demand) | $750 |
| RDS PostgreSQL | db.r5.xlarge, Multi-AZ | $850 |
| ElastiCache Redis | 3x cache.r5.large | $450 |
| S3 Storage | 1 TB | $23 |
| Data Transfer | 500 GB/month | $45 |
| Load Balancer | ALB | $25 |
| CloudWatch | Logs + Metrics | $50 |
| **Total** | | **~$2,265/month** |

**Optimization Potential**:
- Use spot instances: Save ~$500/month on EC2
- Use Aurora Serverless: Save ~$300/month on RDS (if usage is bursty)
- **Optimized Total**: **~$1,465/month**

---

## Terraform Best Practices

### State Management

**Backend Configuration** (S3 + DynamoDB for locking):
```hcl
terraform {
  backend "s3" {
    bucket         = "senzu-ai-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

**State Isolation**: Separate state files per environment

### Workspaces

Use Terraform workspaces for environment separation:
```bash
terraform workspace new prod
terraform workspace select prod
terraform apply
```

### Variable Management

**Sensitive Variables**: Store in AWS Secrets Manager, fetch in Terraform
```hcl
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "senzu-ai/prod/db-password"
}

resource "aws_db_instance" "postgresql" {
  password = data.aws_secretsmanager_secret_version.db_password.secret_string
  # ...
}
```

### Drift Detection

Run weekly drift detection:
```bash
terraform plan -out=tfplan
# Review for unexpected changes
```

---

## Future Enhancements

1. **GitOps with ArgoCD**: Declarative continuous deployment
2. **Service Mesh (Istio)**: Advanced traffic management, mTLS, observability
3. **Chaos Engineering**: Automated failure injection (Chaos Mesh)
4. **Multi-Cluster Management**: Centralized management across regions
5. **Infrastructure Testing**: Terratest for automated infrastructure tests

---

**Last Updated**: 2025-10-15
**Version**: 1.0
**Status**: Phase 3 - Production Readiness
**Owner**: DevOps/SRE Team
