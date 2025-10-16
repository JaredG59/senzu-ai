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

### 📋 Phase 3: Production Readiness (Recommended Next)
7. Caching Strategy Documentation
8. Error Handling & Observability Architecture
9. Security Architecture Details
10. Infrastructure as Code Planning

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

## Technology Stack (Recommended)

### Backend
- **Language**: Python 3.11+ or Node.js (TypeScript)
- **Web Framework**: FastAPI (Python) or Express (Node.js)
- **ORM**: SQLAlchemy (Python) or Prisma (Node.js)
- **API Spec**: OpenAPI 3.0

### Data & ML
- **ML Framework**: XGBoost, LightGBM, PyTorch
- **ML Ops**: MLflow or Weights & Biases
- **Workflow Orchestration**: Airflow or Prefect
- **Feature Store**: Custom (PostgreSQL + S3) or Feast

### Infrastructure
- **Database**: PostgreSQL 14+
- **Cache**: Redis 7+
- **Storage**: AWS S3 / GCS / Azure Blob
- **Container**: Docker
- **Orchestration**: Kubernetes or ECS

### Monitoring
- **Metrics**: Prometheus + Grafana or Datadog
- **Logging**: ELK Stack or CloudWatch
- **Tracing**: Jaeger or OpenTelemetry
- **Alerting**: PagerDuty or Opsgenie

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

## Open Questions / Decisions Needed

1. **Cloud Provider**: AWS, GCP, or Azure?
2. **Programming Language**: Python (ML-friendly) or Node.js (high concurrency)?
3. **Auth Strategy**: JWT only, or OAuth with 3rd party (Auth0)?
4. **Data Provider**: Which sports data API? (The Odds API, SportsData.io, etc.)
5. **Deployment**: Kubernetes, serverless, or managed services?
6. **Frontend**: Separate repo or monorepo? React/Next.js?
7. **Rate Limiting**: Per-user, per-IP, or both?
8. **Monetization**: Free tier + paid tiers? Credits? Subscription?

---

## Resources & References

### Design Documents
- Database Schema: `plantuml/puml/senzu-ai-database-schema.puml`
- API Specification: `api-spec.yaml`
- Service Interfaces: `plantuml/puml/senzu-ai-service-interfaces.puml`
- Workflows: `plantuml/puml/senzu-ai-*-workflow.puml`
- Sequence Diagrams: `plantuml/puml/senzu-ai-*-flow.puml`
- Feature Spec: `docs/feature-engineering-spec.md`

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

**Last Updated**: 2025-10-15
**Version**: 1.0
**Status**: Design Phase Complete - Ready for Implementation
