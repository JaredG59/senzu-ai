# Domain Model

The domain model defines the core entities and their relationships in the Senzu AI system.
This class diagram shows the data structures used throughout the application.

### Core Entities:
- **User**: System users with authentication
- **Sport**: Supported sports (NBA, NFL, etc.)
- **Team**: Sports teams with external provider IDs
- **Match**: Sporting events with teams, scores, and status
- **OddsSnapshot**: Betting odds from various providers at specific timestamps
- **FeatureVector**: Computed features for ML inference
- **ModelRun**: Trained model versions with metadata
- **Prediction**: Probability predictions and expected value calculations
- **BacktestResult**: Historical model performance metrics

## Diagram

![Domain Model](../images/senzu-ai-class-diagram.png)

## Related Diagrams

- [Database Schema](./senzu-ai-database-schema.md)
- [Service Interfaces](./senzu-ai-service-interfaces.md)

## Source

This documentation was automatically generated from PlantUML diagrams.

- Source file: [`../puml/senzu-ai-class-diagram.puml`](../puml/senzu-ai-class-diagram.puml)
- Image: [`../images/senzu-ai-class-diagram.png`](../images/senzu-ai-class-diagram.png)

## Navigation

Return to [Documentation Index](./README.md)
