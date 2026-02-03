# Model Training & Deployment Flow

This sequence diagram shows the end-to-end flow of training a new model and deploying it to production.

### Training Pipeline Steps:
1. **Data Preparation**: Export features and labels from feature store and data lake
2. **Data Splitting**: Time-based split (train/validation/test)
3. **Model Training**: Train with hyperparameters, early stopping, metric tracking
4. **Model Evaluation**: Calculate accuracy, log loss, Brier score, calibration
5. **Backtesting**: Simulate betting strategy to compute ROI and Sharpe ratio
6. **Model Registration**: Save artifact to S3, register in MLflow and database

### Deployment Steps:
1. **Model Review**: ML engineer reviews metrics and performance
2. **Model Activation**: Atomically switch active model in database
3. **Cache Invalidation**: Clear cached models and predictions
4. **Model Warming**: Pre-load new model into memory/cache
5. **Monitoring Setup**: Configure drift detection and performance tracking

### Safety Measures:
- Transaction-based activation prevents inconsistencies
- Rollback procedure documented
- Continuous monitoring for performance degradation

## Diagram

![Model Training & Deployment Flow](../images/senzu-ai-model-deployment-flow.png)

## Related Diagrams

- [Backend Architecture](./senzu-ai-backend-architecture.md)
- [Service Interfaces](./senzu-ai-service-interfaces.md)

## Source

This documentation was automatically generated from PlantUML diagrams.

- Source file: [`../puml/senzu-ai-model-deployment-flow.puml`](../puml/senzu-ai-model-deployment-flow.puml)
- Image: [`../images/senzu-ai-model-deployment-flow.png`](../images/senzu-ai-model-deployment-flow.png)

## Navigation

Return to [Documentation Index](./README.md)
