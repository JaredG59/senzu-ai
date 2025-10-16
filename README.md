# Senzu AI

An AI-powered sports prediction platform that provides probability predictions and expected value (EV) calculations for sports betting markets.

## Overview

Senzu AI ingests real-time sports data from external providers, applies advanced feature engineering, and runs machine learning models to generate actionable betting insights. The system serves predictions through a REST/GraphQL API with comprehensive caching and sub-500ms latency targets.

## Features

- **Real-time Predictions**: Live probability predictions for sports events with expected value calculations
- **Advanced Feature Engineering**: 72-feature model covering team form, head-to-head stats, market odds, contextual factors, and advanced analytics
- **Multi-Market Support**: Predictions across multiple betting markets (Moneyline, Spread, Totals, Props)
- **High Performance**: Sub-50ms cache-hit latency, sub-500ms cold predictions
- **Scalable Architecture**: Microservices design with PostgreSQL partitioning for high-volume data (1M+ odds snapshots/day)
- **RESTful API**: Comprehensive OpenAPI 3.0 specification with 20+ endpoints
- **MLOps Integration**: Model versioning, A/B testing, and performance monitoring

## Architecture

### Core Components

**Service Layer**:
- **API Gateway**: HTTP routing, authentication, rate limiting
- **Auth Service**: JWT-based authentication and user management
- **Inference Service**: Prediction orchestration and EV calculation
- **Feature Service**: Real-time feature engineering and vector building
- **Model Service**: ML model loading and inference execution
- **Data Ingestion Service**: External data fetching and ETL pipelines

**Data Layer**:
- **Match Repository**: Match metadata, scores, and status
- **Odds Repository**: Time-series betting odds (partitioned by date)
- **Feature Repository**: Computed feature vectors for model input
- **Prediction Repository**: Model predictions with EV scores (partitioned by date)

**Infrastructure**:
- PostgreSQL 14+ with table partitioning
- Redis 7+ for caching
- S3/GCS/Azure Blob for data lake
- Airflow/Prefect for workflow orchestration

### Technology Stack (Recommended)

**Backend**:
- Language: Python 3.11+ or Node.js (TypeScript)
- Framework: FastAPI (Python) or Express.js (Node.js)
- ORM: SQLAlchemy or Prisma
- ML: XGBoost, LightGBM, or PyTorch

**Database & Cache**:
- PostgreSQL 14+
- Redis 7+
- AWS S3 / GCS / Azure Blob

**MLOps**:
- MLflow or Weights & Biases
- Model versioning and experiment tracking

## Feature Engineering

The system generates 72 features across 5 categories:

1. **Team Form** (20 features): Recent performance, win/loss streaks, goal metrics
2. **Head-to-Head** (10 features): Historical matchup statistics
3. **Market Odds** (15 features): Implied probabilities, odds movements, bookmaker consensus
4. **Contextual** (12 features): Home/away, rest days, injuries, travel distance
5. **Advanced Stats** (15 features): xG, possession, defensive pressure, set-piece efficiency

See `docs/feature-engineering-spec.md` for complete specifications.

## Performance Targets

- Prediction latency (cache miss): <500ms (p95)
- Prediction latency (cache hit): <50ms
- Feature computation: <100ms
- API uptime: 99.9%
- Database query time: <100ms (p95)

## Project Status

**Current Phase**: Design Complete - Ready for Implementation

The project has completed comprehensive architecture and design documentation. Implementation is ready to begin with Week 1-4 foundation phase.

## Documentation

Comprehensive documentation is available in the `/docs` directory:

- `architecture-summary.md`: Complete system design overview
- `api-spec.yaml`: OpenAPI 3.0 API specification
- `feature-engineering-spec.md`: Detailed feature engineering strategy
- `plantuml/`: Architecture diagrams including database schema, service interfaces, and workflows
- `CLAUDE.md`: Project guidance and development principles

## Getting Started

### Prerequisites

- Python 3.11+ or Node.js 18+
- PostgreSQL 14+
- Redis 7+
- Docker (optional, for containerized deployment)

### Installation

_Coming soon - implementation in progress_

### Configuration

_Coming soon - implementation in progress_

### Running the Application

_Coming soon - implementation in progress_

## API Documentation

The complete API specification is available in `docs/api-spec.yaml`. Key endpoint categories include:

- **Authentication**: `/auth/register`, `/auth/login`, `/auth/refresh`
- **Matches**: `/matches`, `/matches/{matchId}`
- **Predictions**: `/predictions/match/{matchId}`, `/predictions/batch`
- **Odds**: `/odds/match/{matchId}`, `/odds/movements`
- **Models**: `/models`, `/models/{modelId}/performance`
- **Sports Data**: `/sports`, `/leagues`, `/teams`

## Development Roadmap

### Phase 1: Foundation (Weeks 1-4)
- Database schema implementation
- Core service interfaces
- Basic API gateway setup

### Phase 2: Data & Features (Weeks 5-8)
- Data ingestion pipelines
- Feature engineering implementation
- Odds repository with partitioning

### Phase 3: ML & Inference (Weeks 9-12)
- Model training pipeline
- Inference service
- EV calculation engine

### Phase 4: Production (Weeks 13-16)
- Caching layer optimization
- Monitoring and alerting
- Load testing and optimization

## Contributing

_Contributing guidelines coming soon_

## License

_License information to be determined_

## Contact

_Contact information to be added_
