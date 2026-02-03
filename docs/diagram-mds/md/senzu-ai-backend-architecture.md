# Backend Architecture

This diagram illustrates the high-level backend architecture of Senzu AI, showing the main components
and their interactions. The system follows a microservices architecture with clear separation of concerns.

### Key Components:
- **API Gateway**: Entry point for all client requests, handles routing and authentication
- **Inference Service**: Orchestrates the prediction workflow
- **Feature Service**: Handles feature engineering and storage
- **Model Service**: Manages ML model lifecycle and inference
- **Data Ingestion Service**: Fetches data from external sports data providers
- **Data Layer**: PostgreSQL for relational data, Redis for caching, S3 for data lake storage

## Diagram

![Backend Architecture](../images/senzu-ai-backend-architecture.png)

## Related Diagrams

- [Domain Model](./senzu-ai-class-diagram.md)
- [Deployment Architecture](./senzu-ai-deployment-diagram.md)
- [Database Schema](./senzu-ai-database-schema.md)

## Source

This documentation was automatically generated from PlantUML diagrams.

- Source file: [`../puml/senzu-ai-backend-architecture.puml`](../puml/senzu-ai-backend-architecture.puml)
- Image: [`../images/senzu-ai-backend-architecture.png`](../images/senzu-ai-backend-architecture.png)

## Navigation

Return to [Documentation Index](./README.md)
