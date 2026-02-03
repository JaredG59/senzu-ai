# Database Schema (ER Diagram)

The database schema defines all tables, columns, relationships, and indexes used in the PostgreSQL database.
This ER diagram provides a comprehensive view of data storage and relationships.

### Schema Organization:
- **User & Auth**: User authentication and refresh tokens
- **Sports Domain**: Sports, teams, and matches
- **Odds Data**: Time-series odds snapshots (partitioned by month)
- **Feature Store**: Computed feature vectors with versioning
- **Model Management**: Model metadata, evaluations, and backtests
- **Predictions**: Prediction results (partitioned by month)
- **Data Ingestion Tracking**: Job status and error logging

### Performance Optimizations:
- Strategic indexing on frequently queried columns
- Partitioning for large tables (odds_snapshots, predictions)
- JSONB columns for flexible metadata storage

## Diagram

![Database Schema (ER Diagram)](../images/senzu-ai-database-schema.png)

## Related Diagrams


## Source

This documentation was automatically generated from PlantUML diagrams.

- Source file: [`../puml/senzu-ai-database-schema.puml`](../puml/senzu-ai-database-schema.puml)
- Image: [`../images/senzu-ai-database-schema.png`](../images/senzu-ai-database-schema.png)

## Navigation

Return to [Documentation Index](./README.md)
