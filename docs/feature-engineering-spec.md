# Feature Engineering Specification

## Overview
This document defines the feature engineering strategy for the Senzu AI sports prediction system. Features are calculated from historical match data, team statistics, and current betting odds to power ML models.

## Feature Categories

### 1. Team Form Features (20 features)

#### Recent Performance
- `home_win_rate_last_5` - Win rate for home team in last 5 games
- `home_win_rate_last_10` - Win rate for home team in last 10 games
- `home_win_rate_last_20` - Win rate for home team in last 20 games
- `away_win_rate_last_5` - Win rate for away team in last 5 games
- `away_win_rate_last_10` - Win rate for away team in last 10 games
- `away_win_rate_last_20` - Win rate for away team in last 20 games

#### Scoring Statistics
- `home_goals_per_game_last_10` - Average goals scored by home team (last 10)
- `home_goals_conceded_per_game_last_10` - Average goals conceded (last 10)
- `away_goals_per_game_last_10` - Average goals scored by away team (last 10)
- `away_goals_conceded_per_game_last_10` - Average goals conceded (last 10)

#### Home/Away Splits
- `home_team_home_record_win_rate` - Home team's win rate when playing at home
- `away_team_away_record_win_rate` - Away team's win rate when playing away
- `home_team_home_goals_per_game` - Home team's scoring rate at home venue
- `away_team_away_goals_per_game` - Away team's scoring rate at away venues

#### Momentum Features
- `home_momentum_weighted` - Weighted recent results (recent games weighted higher)
  - Formula: `sum(result_i * weight_i) / sum(weight_i)` where weight = 1/sqrt(games_ago)
- `away_momentum_weighted` - Same calculation for away team
- `home_streak` - Current win/loss streak (positive = wins, negative = losses)
- `away_streak` - Current win/loss streak for away team

#### Rest & Fatigue
- `home_days_since_last_match` - Days of rest for home team
- `away_days_since_last_match` - Days of rest for away team

### 2. Head-to-Head Features (10 features)

- `h2h_home_win_rate` - Historical home team win rate in H2H matchups
- `h2h_away_win_rate` - Historical away team win rate in H2H matchups
- `h2h_draw_rate` - Historical draw rate in H2H matchups
- `h2h_total_matches` - Number of historical H2H matches
- `h2h_avg_home_goals` - Average goals by home team in H2H
- `h2h_avg_away_goals` - Average goals by away team in H2H
- `h2h_last_result` - Result of last H2H match (1=home win, 0=draw, -1=away win)
- `h2h_days_since_last_meeting` - Days since last H2H match
- `h2h_home_advantage` - Home advantage factor in H2H history
- `h2h_goal_differential` - Average goal differential in H2H

### 3. Market Odds Features (15 features)

#### Implied Probabilities
- `odds_implied_prob_home_win` - Implied probability from moneyline odds
- `odds_implied_prob_draw` - Implied probability of draw
- `odds_implied_prob_away_win` - Implied probability of away win
- `odds_overround` - Total implied probability (measures bookmaker margin)

#### Odds Movement (if available)
- `odds_home_movement_24h` - Change in home odds over 24 hours
- `odds_away_movement_24h` - Change in away odds over 24 hours
- `odds_volume_indicator` - Relative betting volume (if available from provider)

#### Market Consensus
- `odds_home_avg_across_providers` - Average home odds across providers
- `odds_away_avg_across_providers` - Average away odds across providers
- `odds_home_std_across_providers` - Standard deviation (market agreement)
- `odds_away_std_across_providers` - Standard deviation

#### Spread & Totals
- `spread_line` - Point spread line
- `spread_home_odds` - Odds on home team covering spread
- `total_line` - Over/under line
- `total_over_odds` - Odds on over

### 4. Contextual Features (12 features)

#### Temporal
- `season_progress` - % through season (0.0 to 1.0)
- `day_of_week` - Day of week (0=Monday, 6=Sunday)
- `is_weekend` - Binary indicator for weekend match
- `hour_of_day` - Hour of match start (0-23)
- `time_until_match_hours` - Hours until match starts

#### Situational
- `home_team_league_position` - Current league standing
- `away_team_league_position` - Current league standing
- `league_position_difference` - Absolute difference in standings
- `is_derby` - Binary indicator for local rivalry match
- `match_importance` - Derived importance score (playoffs, relegation battle, etc.)

#### Venue
- `venue_capacity` - Stadium capacity (normalized)
- `venue_attendance_avg` - Average attendance % at venue

### 5. Advanced Statistical Features (15 features)

#### Expected Goals (xG)
- `home_xg_per_game_last_10` - Expected goals for home team (last 10)
- `away_xg_per_game_last_10` - Expected goals for away team (last 10)
- `home_xg_conceded_per_game_last_10` - xG conceded by home team
- `away_xg_conceded_per_game_last_10` - xG conceded by away team
- `home_xg_differential` - Difference between xG and actual goals
- `away_xg_differential` - Difference between xG and actual goals

#### Possession & Efficiency
- `home_avg_possession_last_10` - Average possession % (last 10 games)
- `away_avg_possession_last_10` - Average possession %
- `home_shot_efficiency_last_10` - Goals per shot ratio
- `away_shot_efficiency_last_10` - Goals per shot ratio

#### Defensive Metrics
- `home_clean_sheet_rate_last_10` - % of games without conceding
- `away_clean_sheet_rate_last_10` - % of games without conceding

#### Strength of Schedule
- `home_opponent_avg_strength_last_10` - Average opponent quality faced
- `away_opponent_avg_strength_last_10` - Average opponent quality faced
- `relative_team_strength` - ELO rating difference or similar

---

## Feature Engineering Pipeline

### Data Sources Required
1. **Historical Match Results** (last 2 seasons minimum)
2. **Team Statistics** (goals, possession, shots, etc.)
3. **Current Betting Odds** (multiple markets, multiple providers)
4. **League Standings** (current positions)
5. **Venue Data** (capacity, attendance)
6. **xG Data** (if available from provider)

### Calculation Frequency

#### Real-Time Features (computed on prediction request)
- Odds-based features
- Time until match features
- Days since last match

#### Pre-Computed Features (cached, updated daily)
- Team form features
- H2H features
- Season statistics
- League positions

#### Feature Store Strategy
- **Hot Storage (PostgreSQL)**: Last 6 months of feature vectors
- **Cold Storage (S3 Data Lake)**: All historical features for retraining
- **Cache (Redis)**: Active match features (TTL: 1 hour)

### Normalization & Scaling

#### Numerical Features
- Apply z-score normalization: `(x - mean) / std`
- Clip outliers to [-3, 3] standard deviations
- Store normalization parameters per feature version

#### Categorical Features
- One-hot encoding for low cardinality (<10 categories)
- Target encoding for high cardinality
- Default "unknown" category for new values

### Missing Value Handling

| Feature Type | Strategy |
|--------------|----------|
| Team form (insufficient history) | Use league average |
| H2H (no prior meetings) | Use neutral values (0.5 for rates) |
| Odds movement (no history) | Set movement to 0 |
| xG data (not available) | Substitute with goals-based approximation |

### Feature Versioning

Each feature vector includes `feature_version` field:
- `v1.0` - Initial feature set
- `v1.1` - Added xG features
- `v2.0` - Breaking change (different normalization)

This enables:
- Model backwards compatibility
- A/B testing of feature sets
- Gradual feature rollouts

### Validation Rules

Before accepting a feature vector:
1. All required features present (72 features in v1.0)
2. No NaN or Inf values
3. Numerical features within [-5, 5] range (after normalization)
4. Feature count matches expected for version
5. Timestamp of feature computation logged

### Performance Considerations

**Target Latency**: <100ms for feature computation

**Optimization Strategies**:
- Pre-aggregate team statistics daily
- Cache historical H2H results
- Batch database queries
- Use database indexes on temporal queries
- Materialize common aggregations

**Monitoring**:
- Track feature computation time (p50, p95, p99)
- Alert if >500ms computation time
- Monitor cache hit rates
- Track feature value distributions for drift

---

## Feature Importance & Selection

### Model Training Phase
- Track feature importance from model training
- Remove features with <0.01 importance score
- Monitor for multicollinearity (VIF > 10)
- Iteratively refine feature set

### Feature Drift Detection
- Monitor feature distributions over time
- Alert if distribution shift detected (KS test p < 0.05)
- Potential causes: league rule changes, data source changes

---

## Future Enhancements

### Planned Features (v2.0)
- Player-level statistics (injuries, suspensions, key players)
- Weather conditions (temperature, precipitation, wind)
- Travel distance for away team
- Referee statistics (cards, penalties)
- Social sentiment indicators (if data available)
- Transfer window activity impact

### Advanced Feature Engineering
- Automated feature generation (Featuretools)
- Deep learning embeddings for teams/players
- Time-series features (LSTM-based)
- Graph features (team relationship networks)
