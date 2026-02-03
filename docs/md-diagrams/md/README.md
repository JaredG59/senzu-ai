# Senzu AI Architecture Documentation

This directory contains automatically generated documentation from PlantUML diagrams.
Each document includes a rendered diagram image and detailed descriptions of the components and flows.

## Architecture Diagrams

### System Overview
- [Backend Architecture](./senzu-ai-backend-architecture.md) - High-level system architecture and component interactions
- [Deployment Architecture](./senzu-ai-deployment-diagram.md) - Cloud deployment and infrastructure components

### Data Models
- [Domain Model](./senzu-ai-class-diagram.md) - Core entities and their relationships
- [Database Schema](./senzu-ai-database-schema.md) - Complete database schema with tables, indexes, and partitioning
- [Service Interfaces](./senzu-ai-service-interfaces.md) - Service contracts and DTOs

### Process Flows
- [Prediction Request Flow](./senzu-ai-sequence-diagram.md) - High-level prediction flow
- [Detailed Prediction Flow](./senzu-ai-prediction-flow-detailed.md) - Comprehensive prediction workflow with all steps
- [Data Ingestion Sequence](./senzu-ai-ingestion-sequence.md) - Data ingestion from external providers
- [Data Ingestion Workflow](./senzu-ai-data-ingestion-workflow.md) - Ingestion workflow with decision points

### ML & Features
- [Feature Engineering Pipeline](./senzu-ai-feature-pipeline.md) - Feature computation and transformation flow
- [Model Training & Deployment](./senzu-ai-model-deployment-flow.md) - End-to-end ML model lifecycle

## About

These diagrams provide a comprehensive view of the Senzu AI sports prediction system, covering:
- System architecture and components
- Data models and database design
- API workflows and service interactions
- ML pipeline and feature engineering
- Data ingestion and processing

### Regenerating Documentation

To regenerate this documentation from PlantUML source files:

```bash
cd docs/plantuml
python generate_docs.py
```

### Project Structure

```
docs/plantuml/
├── puml/              # PlantUML source files (.puml)
├── images/            # Generated PNG images
├── md/                # Generated Markdown documentation
├── generate_docs.py   # Documentation generator script
└── README.md          # This file
```

## Navigation

- [Project README](../../README.md)
- [Claude AI Instructions](../CLAUDE.md)
