# Senzu AI - Backend Architecture Summary

## Overview
This document provides a comprehensive summary of the Senzu AI backend architecture design, referencing all planning artifacts created during the design phase.

## Architecture Planning Status

### ✅ Phase 1: Critical Foundation (Complete)
1. **Database Schema Design** - `plantuml/puml/senzu-ai-database-schema.puml`
2. **API Contract Definition** - `api-spec.yaml`
3. **Service Interface Definitions** - `plantuml/puml/senzu-ai-service-interfaces.puml`

### ✅ Phase 2: Core Workflows (Complete)
4. **Data Ingestion Workflow** - `plantuml/puml/senzu-ai-data-ingestion-workflow.puml`
5. **Feature Engineering Pipeline** - `plantuml/puml/senzu-ai-feature-pipeline.puml`
6. **Detailed Sequence Diagrams**:
   - Prediction Request Flow - `plantuml/puml/senzu-ai-prediction-flow-detailed.puml`
   - Model Deployment Flow - `plantuml/puml/senzu-ai-model-deployment-flow.puml`
   - Ingestion Sequence - `plantuml/puml/senzu-ai-ingestion-sequence.puml`

### ✅ Phase 3: Production Readiness (Complete)
7. **Caching Strategy Documentation** - `docs/strategy-mds/caching-strategy.md`
8. **Error Handling & Observability Architecture** - `docs/strategy-mds/error-handling-observability.md`
9. **Security Architecture Details** - `docs/strategy-mds/security-architecture.md`
10. **Infrastructure as Code Planning** - `docs/strategy-mds/infrastructure-as-code.md`

### 🚀 Next Phase: Implementation
With all planning phases complete, the project is ready to begin implementation following the "Next Implementation Steps" outlined below.

---

## System Components

### Service Layer
| Service | Purpose | Key Dependencies |
|---------|---------|-----------------|
| **API Gateway** | HTTP entry point, routing, auth verification | Auth Service, Redis Cache |
| **Auth Service** | JWT authentication, user management | PostgreSQL |
| **Inference Service** | Prediction orchestration, EV calculation | Feature Service, Model Service, Redis |
| **Feature Service** | Feature engineering, vector building | Match Repo, Odds Repo, Feature Repo |
| **Model Service** | Model loading, inference execution | S3, Redis, PostgreSQL |
| **Data Ingestion Service** | External data fetching, ETL | Match Repo, Odds Repo, External APIs |

### Data Layer
| Repository | Purpose | Storage |
|------------|---------|---------|
| **Match Repository** | Match metadata, scores, status | PostgreSQL |
| **Odds Repository** | Betting odds snapshots | PostgreSQL (partitioned) |
| **Feature Repository** | Computed feature vectors | PostgreSQL + S3 Data Lake |
| **Prediction Repository** | Model predictions, EV | PostgreSQL (partitioned) |

### Infrastructure
- **PostgreSQL**: Primary relational database
  - Partitioned tables: `odds_snapshots`, `predictions`
  - Retention: 12-24 months hot data
  - Archive to S3 for historical data
- **Redis**: Caching layer
  - Prediction caches (TTL: 5 min)
  - Model caches (TTL: 1-2 hours)
  - Feature caches (TTL: 1 hour)
- **S3 / Data Lake**: Long-term storage
  - Historical features (Parquet format)
  - Model artifacts
  - Archived predictions

---

## Data Flows

### 1. Prediction Request Flow
```
User Request → API Gateway → Auth Check → Cache Check
                    ↓ (cache miss)
              Inference Service
                    ↓
        ┌───────────┴───────────┐
        ↓                       ↓
  Feature Service         Model Service
        ↓                       ↓
  [Build Features]        [Load Model]
  [72-dim vector]         [Run Inference]
        ↓                       ↓
        └───────────┬───────────┘
                    ↓
            [Calculate EV]
            [Store Predictions]
            [Cache Results]
                    ↓
              Return to User
```

**Key Metrics**:
- Target latency: <500ms (p95)
- Cache hit rate: >80% (during match hours)
- Feature computation: <100ms

### 2. Data Ingestion Flow
```
Cron/Scheduler → Ingestion Service
                        ↓
              [Fetch from Provider API]
                        ↓
              [Validate & Transform]
                        ↓
           ┌────────────┴────────────┐
           ↓                         ↓
    [Upsert Matches]        [Insert Odds Snapshots]
           ↓                         ↓
    Match Repository          Odds Repository
           ↓                         ↓
           └────────────┬────────────┘
                        ↓
              [Invalidate Caches]
              [Queue Feature Computation]
```

**Schedule**:
- Odds updates: Every 5 minutes
- Match schedule: Every 1 hour
- Historical data: Daily

### 3. Model Training & Deployment Flow
```
ML Engineer → Training Pipeline
                    ↓
        [Fetch Features from Data Lake]
        [Fetch Actual Outcomes]
                    ↓
        [Train Model (XGBoost/etc)]
                    ↓
        [Evaluate (Test Set + Backtest)]
                    ↓
        [Upload Artifact to S3]
        [Register in MLflow]
                    ↓
        [Manual Review by Engineer]
                    ↓
        [Activate Model in Model Service]
                    ↓
        [Invalidate Model & Prediction Caches]
```

**Evaluation Criteria**:
- Accuracy: >55%
- Backtest ROI: >0%
- Brier score: <0.25
- Calibration error: <5%

---

## API Endpoints Summary

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout user

### Core Prediction API
- `GET /matches/{matchId}/predictions` - Get predictions for match
- `GET /predictions` - List predictions with filters (EV, market, date)

### Match & Odds Data
- `GET /matches` - List matches (filtered by date, sport, status)
- `GET /matches/{matchId}` - Match details
- `GET /matches/{matchId}/odds` - Odds snapshots for match

### Model Management
- `GET /models` - List model versions
- `GET /models/{modelId}` - Model details
- `GET /models/{modelId}/evaluations` - Model metrics
- `GET /models/{modelId}/backtest` - Backtest results

### Sports Metadata
- `GET /sports` - List sports
- `GET /sports/{sportId}/teams` - List teams

---

## Database Schema Highlights

### Core Tables
- `users`, `refresh_tokens` - Authentication
- `sports`, `teams`, `matches` - Sports domain
- `odds_snapshots` - Betting odds (partitioned by month)
- `feature_vectors` - Computed features
- `model_runs`, `model_evaluations` - Model management
- `predictions` - AI predictions (partitioned by month)
- `backtest_results` - Model backtesting
- `ingestion_jobs` - ETL job tracking

### Partitioning Strategy
**odds_snapshots** (partition by `timestamp`):
- ~1M rows/day expected
- Partition by month
- Retain 24 months, archive to S3

**predictions** (partition by `predicted_at`):
- High volume during peak hours
- Partition by month
- Retain 12 months, archive to S3

### Key Indexes
- Composite index: `(match_id, provider, market, timestamp)` on odds_snapshots
- Composite index: `(match_id, model_run_id, market)` on predictions
- Index on `external_match_id` for provider lookups
- Index on `start_at` for date range queries
- Index on `expected_value` for high-EV queries

---

## Feature Engineering

### Feature Categories (72 features in v1.0)
1. **Team Form** (20 features) - Win rates, scoring, home/away splits, momentum
2. **Head-to-Head** (10 features) - H2H history, results, goal differentials
3. **Market Odds** (15 features) - Implied probabilities, odds movement, consensus
4. **Contextual** (12 features) - Temporal, situational, venue
5. **Advanced Stats** (15 features) - xG, possession, efficiency, strength of schedule

### Feature Computation
- **Real-time**: Odds features, temporal features (computed on request)
- **Pre-computed**: Team form, H2H stats (cached, updated daily)
- **Storage**: PostgreSQL (6 months) + S3 Data Lake (all historical)
- **Versioning**: `feature_version` field enables A/B testing and reproducibility

**Detailed spec**: `docs/feature-engineering-spec.md`

---

## Performance Targets

### Latency (p95)
- Prediction request (cache miss): <500ms
- Prediction request (cache hit): <50ms
- Feature computation: <100ms
- Model inference: <200ms
- Data ingestion job: <2 minutes

### Throughput
- Concurrent users: 1,000
- Predictions/second: 100
- Ingestion: 10K matches/day, 1M odds/day

### Availability
- API uptime: 99.9%
- Cache hit rate: >80% during peak hours
- Data freshness: Odds <5 minutes old

---

## Technology Stack

### Backend
- **Cloud Provider**: AWS
- **Language**: Python 3.11+
- **Web Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0+
- **API Spec**: OpenAPI 3.0 (auto-generated by FastAPI)
- **API Style**: REST

### Data & ML
- **ML Framework**: XGBoost + scikit-learn
- **ML Ops**: MLflow (self-hosted)
- **Workflow Orchestration**: Airflow (future - manual jobs for MVP)
- **Feature Store**: Custom (PostgreSQL + S3)
- **Data Provider**: The Odds API (MVP), multi-provider later

### Infrastructure
- **Database**: PostgreSQL 14+
- **Cache**: Redis 7+
- **Storage**: AWS S3
- **Container**: Docker
- **Orchestration**: ECS Fargate (MVP) → EKS/Kubernetes (scale)
- **IaC**: Terraform
- **CI/CD**: GitHub Actions
- **Container Registry**: AWS ECR

### Frontend
- **Framework**: Next.js 14+ (React)
- **Language**: TypeScript
- **Deployment**: Vercel (free tier)
- **API Client**: OpenAPI Generator (type-safe client)

### Monitoring
- **Observability Platform**: DataDog (unified metrics, logs, traces, APM)
- **Instrumentation**: DataDog Agent + SDKs
- **Alerting**: DataDog Alerts + PagerDuty integration
- **Dashboards**: DataDog built-in dashboards

### Security
- **Authentication**: Custom JWT (RS256) - MVP
- **Future Auth**: Auth0/Clerk (OAuth, social login, MFA)
- **Secrets**: AWS Secrets Manager
- **WAF**: AWS WAF
- **CDN/DDoS**: CloudFront + AWS Shield

---

## Next Implementation Steps

### Phase 1: Foundation (Weeks 1-4)
1. Set up project structure and dev environment
2. Implement database schema (migrations)
3. Build Auth Service + API Gateway skeleton
4. Set up CI/CD pipelines

### Phase 2: Data Ingestion (Weeks 5-8)
5. Implement Data Ingestion Service
6. Connect to sports data provider APIs
7. Build Match & Odds Repositories
8. Set up scheduled ingestion jobs

### Phase 3: Feature Engineering (Weeks 9-12)
9. Implement Feature Service
10. Build feature computation logic (all 72 features)
11. Set up Feature Repository
12. Export pipeline to S3 Data Lake

### Phase 4: ML Infrastructure (Weeks 13-16)
13. Build Model Service
14. Set up model training pipeline
15. Integrate MLflow for model registry
16. Implement model deployment workflow

### Phase 5: Inference & API (Weeks 17-20)
17. Implement Inference Service
18. Build prediction endpoints
19. Integrate caching layer
20. End-to-end testing

### Phase 6: Production Hardening (Weeks 21-24)
21. Security audit & hardening
22. Performance optimization
23. Monitoring & alerting setup
24. Documentation & runbooks

---

## Risk Mitigation

### Technical Risks
| Risk | Mitigation |
|------|------------|
| Data provider API downtime | Multiple provider support, fallback data sources |
| Model performance degradation | Continuous monitoring, automated rollback, A/B testing |
| High latency at scale | Caching, read replicas, CDN for static content |
| Database growth | Partitioning, archival to S3, retention policies |

### Business Risks
| Risk | Mitigation |
|------|------------|
| Inaccurate predictions | Rigorous backtesting, conservative EV thresholds |
| Data provider costs | Negotiate pricing, optimize API calls, caching |
| Regulatory/legal | Terms of service compliance, legal review |

---

## Technology Decisions

### Core Technology Stack

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Cloud Provider** | AWS | Most mature ecosystem, excellent managed services (RDS, ElastiCache, S3, ECS), strong ML/AI tools (SageMaker), best Terraform support, cost-effective for startups |
| **Programming Language** | Python 3.11+ (FastAPI) | ML-first system benefits from single language, native ML ecosystem (XGBoost, scikit-learn, pandas), FastAPI provides excellent async performance (100+ req/sec achievable), simpler development and deployment |
| **Web Framework** | FastAPI | Modern async framework, automatic OpenAPI docs, excellent performance, type safety with Pydantic, native async/await support |
| **ORM** | SQLAlchemy 2.0+ | Industry standard for Python, excellent PostgreSQL support, async support, type hints, migration tools (Alembic) |

### Infrastructure Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Deployment (MVP)** | AWS ECS Fargate or App Runner | Managed container orchestration, simpler than Kubernetes, auto-scaling built-in, cost-effective (~$400/month vs ~$1500 for K8s), containerized for portability |
| **Deployment (Scale)** | Migrate to Kubernetes (EKS) | When traffic justifies (~10k+ req/hour), K8s provides more control, better resource utilization, vendor-agnostic, easier multi-region |
| **IaC Tool** | Terraform | Vendor-agnostic, excellent AWS support, mature ecosystem, state management, reusable modules |
| **CI/CD** | GitHub Actions | Native GitHub integration, free for public repos, extensive action marketplace, simple YAML config |
| **Container Registry** | AWS ECR | Native AWS integration, private registry, image scanning, lifecycle policies |

### Authentication & Authorization

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Auth Strategy (MVP)** | Custom JWT (RS256) | Full control, zero additional costs, sufficient for MVP, well-documented in security architecture |
| **Auth Strategy (Future)** | Add OAuth + Auth0/Clerk | Once revenue justifies cost ($25-100/month), add social logins and MFA as premium features |
| **Rate Limiting** | Both per-IP and per-user | Layered approach: per-IP (100 req/min) for DDoS protection, per-user (60-600 req/min) based on tier, per-endpoint for expensive operations |

### Data & ML

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Data Provider (MVP)** | The Odds API | Free tier (500 req/month) sufficient for development, good coverage of major sports, simple REST API, easy to switch providers later (design for provider-agnostic interface) |
| **Data Provider (Scale)** | Multi-provider strategy | Add API-FOOTBALL, SportsData.io, or others as needed, aggregate across providers for reliability and coverage |
| **ML Framework** | XGBoost + scikit-learn | Industry standard for tabular data, excellent performance, interpretable, good Python support |
| **MLOps Platform** | MLflow (self-hosted) | Open-source, model registry, experiment tracking, model versioning, can migrate to managed service later |

### Frontend & API

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Frontend Framework** | Next.js 14+ (React) | Modern React framework, SSR/SSG support, excellent developer experience, Vercel deployment (free tier), API routes for BFF pattern |
| **Repository Structure** | Separate repos | Backend and frontend in separate repos initially, simpler for small team, independent deployment cycles, can migrate to monorepo if coordination becomes complex |
| **API Documentation** | OpenAPI 3.0 (auto-generated by FastAPI) | FastAPI generates OpenAPI spec automatically, use OpenAPI Generator for TypeScript client, ensures type safety across stack |
| **API Style** | REST | Simpler than GraphQL for MVP, well-understood, good caching support, sufficient for current use cases |

### Monetization Strategy

| Tier | Price | Features | Rate Limit |
|------|-------|----------|------------|
| **Free** | $0/month | 10 predictions/day, read-only access to matches/odds | 60 req/min |
| **Premium** | $29/month | Unlimited predictions, full API access, historical data | 600 req/min |
| **Pro** | $99/month | Everything + backtest access, priority support, analytics dashboard, higher rate limits | 1200 req/min |

**Rationale**: Freemium model provides low-friction user acquisition, clear conversion path when users hit limits, predictable subscription revenue, can add pay-as-you-go credits later if needed.

### Monitoring & Observability

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Observability Platform** | DataDog | Unified platform for metrics, logs, traces, and APM in one place; much faster setup than open-source stack (hours vs days); excellent out-of-box dashboards; strong Python/FastAPI support; cost-effective for small teams (~$100-200/month for 5-10 hosts); reduces operational overhead; easy PagerDuty integration |
| **Instrumentation** | DataDog Agent + ddtrace (Python SDK) | Native DataDog agents, automatic instrumentation for FastAPI/Flask/Django, distributed tracing built-in, custom metrics via StatsD |
| **Alerting** | DataDog Monitors + PagerDuty | DataDog monitors for threshold/anomaly detection, intelligent alerting with ML-based anomaly detection, native PagerDuty integration for on-call |
| **Log Management** | DataDog Logs | Centralized log aggregation, automatic parsing of JSON logs, log-to-metrics conversion, retention policies, easy correlation with traces |
| **APM** | DataDog APM | Application Performance Monitoring, automatic service maps, request tracing, performance profiling, bottleneck identification |

---

## Resources & References

### Design Documents

#### Phase 1 & 2: Foundation & Core Workflows
- Database Schema: `plantuml/puml/senzu-ai-database-schema.puml`
- API Specification: `api-spec.yaml`
- Service Interfaces: `plantuml/puml/senzu-ai-service-interfaces.puml`
- Workflows: `plantuml/puml/senzu-ai-*-workflow.puml`
- Sequence Diagrams: `plantuml/puml/senzu-ai-*-flow.puml`
- Feature Spec: `docs/feature-engineering-spec.md`

#### Phase 3: Production Readiness
- Caching Strategy: `docs/strategy-mds/caching-strategy.md`
- Error Handling & Observability: `docs/strategy-mds/error-handling-observability.md`
- Security Architecture: `docs/strategy-mds/security-architecture.md`
- Infrastructure as Code: `docs/strategy-mds/infrastructure-as-code.md`

### Original Diagrams
- High-level Architecture: `plantuml/puml/senzu-ai-backend-architecture.puml`
- Class Diagram: `plantuml/puml/senzu-ai-class-diagram.puml`
- Basic Sequence: `plantuml/puml/senzu-ai-sequence-diagram.puml`
- Deployment: `plantuml/puml/senzu-ai-deployment-diagram.puml`

### External Resources
- OpenAPI Specification: https://swagger.io/specification/
- PlantUML Documentation: https://plantuml.com/
- Sports Betting Data Providers: The Odds API, SportsData.io
- MLOps Best Practices: https://ml-ops.org/

---

**Last Updated**: 2026-02-02
**Version**: 1.2
**Status**: All Planning Phases Complete - Technology Decisions Finalized - Ready for Implementation
