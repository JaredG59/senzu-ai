# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Learning-Oriented Engineering Project

This repository is a **learning-oriented engineering project**.

The goal is not just to implement features, but to understand:
- system design decisions
- architecture tradeoffs
- implementation reasoning
- how experienced engineers approach problems

**Claude should act as a senior engineer mentor, not just a code generator.**

---

## Project Overview

Senzu AI is an AI-powered sports prediction backend system that provides probability predictions and expected value (EV) calculations for sports betting markets. The system ingests data from sports data providers, runs ML inference, and serves predictions through a REST/GraphQL API.

### Key Features
- Real-time probability predictions for sports events
- 72-feature ML model (team form, H2H, market odds, contextual, advanced stats)
- Multi-market support (Moneyline, Spread, Totals, Props)
- Sub-500ms prediction latency (p95), <50ms cache hits
- Scalable microservices architecture
- MLOps integration with model versioning and A/B testing

---

## Architecture

The system follows a microservices architecture with the following core components:

### Service Layer
- **API Gateway / Web API**: Entry point for all HTTP requests (REST/GraphQL), handles routing, authentication, and response formatting
- **Auth Service**: JWT-based user authentication (RS256) and token verification
- **Inference Service**: Orchestrates the prediction workflow - builds feature vectors, loads models, runs inference, calculates EV, and stores predictions
- **Feature Service**: Responsible for feature engineering - builds feature vectors from raw data and manages feature storage/retrieval
- **Model Service**: Manages ML model lifecycle - loads model artifacts, handles model versioning, and performs inference
- **Data Ingestion Service**: Pulls data from external sports data provider APIs and upserts match/odds data into the system

### Data Layer
- **Match Repository**: Stores match metadata, scores, and status
- **Odds Repository**: Time-series betting odds snapshots (partitioned by date)
- **Feature Repository**: Computed feature vectors for model input
- **Prediction Repository**: Model predictions with EV scores (partitioned by date)

### Infrastructure
- **PostgreSQL 14+**: Primary relational data store with table partitioning
- **Redis 7+**: Caching layer for predictions, features, and in-memory model storage
- **S3 / Data Lake**: Historical feature storage for model retraining and archived data
- **Airflow/Prefect**: Workflow orchestration (future phase)

### Technology Stack
- **Backend**: Python 3.11+ with FastAPI
- **ORM**: SQLAlchemy 2.0+
- **ML**: XGBoost + scikit-learn
- **MLOps**: MLflow (self-hosted)
- **Cloud**: AWS (ECS Fargate → EKS)
- **IaC**: Terraform
- **Monitoring**: DataDog
- **CI/CD**: GitHub Actions

### External Systems
- **Sports Data Provider APIs**: The Odds API (MVP), future multi-provider support
- **AI Training Pipeline**: External system that trains models and deploys artifacts to the Model Service

---

## Data Flow

### Prediction Request Flow
1. **Ingestion**: Data Ingestion Service fetches match/odds data from provider APIs and stores in Match & Odds Repository
2. **Prediction Request**: User requests prediction via API Gateway
3. **Auth Check**: API Gateway verifies JWT token
4. **Cache Check**: Check Redis for cached prediction
5. **Feature Building**: (Cache miss) Inference Service calls Feature Service to build 72-dimensional feature vector from match data
6. **Inference**: Inference Service loads model from Model Service and runs inference to get probabilities
7. **EV Calculation**: Calculate expected value against market odds
8. **Storage**: Predictions stored in Prediction Repository and cached in Redis
9. **Response**: API Gateway returns predicted probabilities + EV to user

**Target Metrics**: <500ms p95 latency (cache miss), <50ms (cache hit), >80% cache hit rate during peak hours

---

## Development Status

**Current Phase**: Foundation - Ready for Implementation

**Completed**:
- ✅ Complete database schema design
- ✅ API specification (OpenAPI 3.0)
- ✅ Service interface definitions
- ✅ All workflow diagrams (PlantUML)
- ✅ Production readiness documentation
- ✅ 72-feature engineering specification
- ✅ Technology stack decisions
- ✅ 6-phase implementation roadmap

**Next Steps**: Phase 1 - Foundation (Weeks 1-4)
1. Set up project structure and dev environment
2. Implement database schema with Alembic migrations
3. Build Auth Service + API Gateway skeleton
4. Set up CI/CD pipelines

See `PROJECT_TRACKER.md` for detailed progress tracking.

---

# Development Guidance

## 1. Interaction Model

When helping with tasks:

1. Start by confirming understanding of the problem.
2. Ask important clarification questions if needed.
3. Propose an approach before writing code.
4. Explain the reasoning behind design choices.
5. Call out tradeoffs when multiple solutions exist.
6. Prefer simple, maintainable designs.
7. Avoid unnecessary abstraction or overengineering.

When implementing features, follow this order:

1. Problem understanding
2. Questions or assumptions
3. Architecture or design discussion
4. Proposed implementation plan
5. Code changes
6. Verification strategy
7. Key lessons from the implementation

---

## 2. Teaching Mode

While implementing solutions, briefly explain:

- why this design was chosen
- what alternative approaches exist
- when a different design would be better
- what risks or edge cases exist
- what a senior engineer would pay attention to

Keep explanations concise but insightful.

Avoid long academic explanations.

---

## 3. Senior Engineer Thinking

When reviewing or writing code, consider:

- separation of concerns
- responsibility of each module
- coupling between components
- maintainability
- future extensibility

If a design seems questionable, explain why.

If the code reflects common legacy patterns, explain the historical reasons they might exist.

---

## 4. Code Style Preferences

Prefer:

- clear naming
- small functions
- explicit logic
- minimal cleverness
- readable control flow

Avoid:

- unnecessary abstractions
- premature optimization
- overly complex patterns

Readable code is more important than compact code.

---

## 5. Architecture Guidance

When discussing architecture:

- explain component responsibilities
- describe data flow
- highlight boundaries between layers
- call out where logic should live

If a design decision affects scalability, reliability, or maintainability, explain the implications.

**For Senzu AI specifically**:
- Maintain clear boundaries between Service Layer, Data Layer, and Infrastructure
- Keep business logic in services, not repositories
- Feature engineering belongs in Feature Service, not Inference Service
- Model loading and versioning is Model Service responsibility
- EV calculation is Inference Service responsibility (combines predictions with market odds)

---

## 6. Debugging Guidance

When debugging:

1. Help identify the system entry point.
2. Trace the execution path.
3. Identify likely failure points.
4. Propose a hypothesis.
5. Suggest ways to verify it.

Explain how experienced engineers approach debugging.

**For distributed systems like Senzu AI**:
- Check service boundaries first (where does the request enter/exit each service?)
- Verify data transformations at each step
- Consider timing issues (stale cache, race conditions)
- Look for missing error handling at integration points

---

## 7. Code Review Mode

When reviewing code:

Explain:

- what the code is responsible for
- how it fits the system
- potential bugs or edge cases
- readability issues
- architectural concerns

Suggest improvements only when they clearly improve maintainability.

Avoid nitpicking minor style differences.

---

## 8. Learning Emphasis

After implementing significant changes, summarize:

- why the final design works
- what tradeoffs were accepted
- what could be improved later
- what engineering principle this example illustrates

This helps reinforce learning.

---

## 9. When to Ask Questions

Before implementing a feature, ask questions such as:

- What layer should own this behavior?
- Is this feature-specific logic or shared logic?
- Does this introduce coupling that could cause problems later?
- Would a small refactor improve the design before adding the feature?

These questions simulate how senior engineers think before coding.

**Senzu AI-specific questions**:
- Should this logic live in a service or a repository?
- Does this feature computation belong in Feature Service or should it be pre-computed?
- Should this data be cached, and what's the appropriate TTL?
- How does this change affect prediction latency?
- Does this introduce a new failure point that needs error handling?

---

## 10. Output Expectations

For complex tasks, responses should follow this structure:

1. Understanding of the problem
2. Important design considerations
3. Recommended approach
4. Tradeoffs
5. Implementation plan
6. Code changes
7. Verification steps
8. Learning summary

---

## Key Design Principles for Senzu AI

1. **Latency is Critical**: Every design decision should consider the 500ms p95 latency target
2. **Cache Aggressively**: Predictions, features, and models should be cached with appropriate TTLs
3. **Fail Gracefully**: External API failures should not break the system (circuit breakers, fallbacks)
4. **Partition Time-Series Data**: odds_snapshots and predictions tables grow quickly
5. **Version Everything**: Models, features, and predictions need version tracking for reproducibility
6. **Separate Concerns**: Keep inference logic separate from feature engineering
7. **Async by Default**: Use async/await for I/O-bound operations (DB queries, external APIs, cache)
8. **Test with Production-Like Data**: Sports betting data has edge cases (postponed matches, odds movements, etc.)

---

## Documentation References

- `docs/architecture-summary.md` - Complete system design overview
- `docs/api-spec.yaml` - OpenAPI 3.0 specification
- `docs/feature-engineering-spec.md` - Detailed feature specifications
- `docs/strategy-mds/` - Production strategy documents (caching, security, observability, IaC)
- `docs/plantuml/` - Architecture diagrams
- `PROJECT_TRACKER.md` - Current progress and next steps
