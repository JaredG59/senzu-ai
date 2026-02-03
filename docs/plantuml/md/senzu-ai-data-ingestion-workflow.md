# Data Ingestion Workflow

This activity diagram provides an overview of the data ingestion workflow, showing decision
points, error handling, and post-processing actions.

### Workflow Phases:
1. **Data Fetching**: Call external provider APIs with authentication and rate limiting
2. **Data Validation**: Schema validation, duplicate detection, error filtering
3. **Data Transformation**: Map to internal schema, enrich with metadata
4. **Data Persistence**: Transactional upsert of matches and bulk insert of odds
5. **Post-Processing**: Feature computation triggering, cache invalidation, metrics tracking

### Error Handling Strategy:
- **Retryable Errors**: Network timeouts, rate limits (429), server errors (500/502/503)
- **Non-Retryable Errors**: Authentication failures (401), bad requests (400)
- **Partial Failures**: Continue with valid records, log invalid records separately

### Trigger Sources:
- Scheduled cron jobs (every 5 minutes)
- Manual API triggers
- Webhooks from providers
- Event-driven (match status changes)

### Performance Considerations:
- Bulk operations reduce database round trips
- Batch size typically 1000 records per insert
- Transaction management ensures data consistency

## Diagram

![Data Ingestion Workflow](../images/senzu-ai-data-ingestion-workflow.png)

## Related Diagrams

- [Backend Architecture](./senzu-ai-backend-architecture.md)
- [Service Interfaces](./senzu-ai-service-interfaces.md)

## Source

This documentation was automatically generated from PlantUML diagrams.

- Source file: [`../puml/senzu-ai-data-ingestion-workflow.puml`](../puml/senzu-ai-data-ingestion-workflow.puml)
- Image: [`../images/senzu-ai-data-ingestion-workflow.png`](../images/senzu-ai-data-ingestion-workflow.png)

## Navigation

Return to [Documentation Index](./README.md)
