# Deployment Architecture

The deployment diagram shows how the Senzu AI system is deployed in a cloud environment
(AWS/GCP) with infrastructure components and their relationships.

### Infrastructure Components:
- **API / Web Layer**: API Gateway and Auth Service (containerized)
- **Backend Services**: Inference, Feature, Model, and Ingestion services (containerized)
- **Persistence & Cache**: PostgreSQL RDS, S3 Data Lake, Redis Cache
- **ML Pipeline**: Airflow/Prefect for orchestration, MLflow for model registry

### Scalability Considerations:
- Services are containerized for easy scaling
- Database uses RDS for managed operations
- S3 provides unlimited storage for historical data
- Redis cache improves read performance

## Diagram

![Deployment Architecture](../images/senzu-ai-deployment-diagram.png)

## Related Diagrams


## Source

This documentation was automatically generated from PlantUML diagrams.

- Source file: [`../puml/senzu-ai-deployment-diagram.puml`](../puml/senzu-ai-deployment-diagram.puml)
- Image: [`../images/senzu-ai-deployment-diagram.png`](../images/senzu-ai-deployment-diagram.png)

## Navigation

Return to [Documentation Index](./README.md)
