# Feature Engineering Pipeline

This activity diagram shows the feature engineering pipeline, which transforms raw match
and odds data into feature vectors suitable for ML inference.

### Feature Categories:
1. **Team Form Features**: Win rates, points per game, momentum, home/away splits
2. **Head-to-Head Features**: Historical matchup statistics and trends
3. **Market Odds Features**: Implied probabilities, odds movement, market consensus
4. **Contextual Features**: Rest days, season progress, time of day, home advantage
5. **Statistical Features**: Expected goals (xG), possession, shot efficiency

### Pipeline Phases:
1. **Data Retrieval**: Fetch match, team, odds, and historical data
2. **Feature Computation**: Parallel computation of feature categories
3. **Aggregation**: Combine all features into single vector
4. **Transformation**: Normalize, scale, encode, handle missing values
5. **Validation**: Check for NaN/Inf, validate ranges and schema
6. **Storage**: Save to database and cache in Redis
7. **Export**: Queue for S3 data lake export (for training)

### Performance:
- Parallel feature computation reduces latency
- Caching prevents redundant calculations
- Typical computation time: 200-500ms

## Diagram

![Feature Engineering Pipeline](../images/senzu-ai-feature-pipeline.png)

## Related Diagrams


## Source

This documentation was automatically generated from PlantUML diagrams.

- Source file: [`../puml/senzu-ai-feature-pipeline.puml`](../puml/senzu-ai-feature-pipeline.puml)
- Image: [`../images/senzu-ai-feature-pipeline.png`](../images/senzu-ai-feature-pipeline.png)

## Navigation

Return to [Documentation Index](./README.md)
