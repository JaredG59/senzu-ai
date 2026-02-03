# Caching Strategy Documentation

## Overview
This document defines the comprehensive caching strategy for the Senzu AI system. Effective caching is critical for achieving target latency (<500ms p95) and reducing load on downstream services and databases.

## Caching Architecture

### Cache Layers

```
┌─────────────────────────────────────────────────┐
│                 API Gateway                      │
│            (Response Caching)                    │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│              Redis Cache Layer                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐│
│  │Predictions │  │  Models    │  │  Features  ││
│  │  (5 min)   │  │ (1-2 hrs)  │  │  (1 hour)  ││
│  └────────────┘  └────────────┘  └────────────┘│
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│           Application Cache                      │
│        (In-Memory - per service)                 │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│            PostgreSQL                            │
│        (Query Result Cache)                      │
└──────────────────────────────────────────────────┘
```

### Cache Types

| Cache Type | Technology | Use Case | TTL |
|------------|------------|----------|-----|
| **Distributed Cache** | Redis Cluster | Predictions, features, models | Variable |
| **Application Cache** | In-memory (LRU) | Configuration, metadata | Process lifetime |
| **HTTP Cache** | API Gateway | Public API responses | 1-5 minutes |
| **Database Cache** | PostgreSQL Shared Buffers | Query results | Automatic |

---

## Cache Policies by Data Type

### 1. Prediction Results

**Cache Key Pattern**: `prediction:{match_id}:{model_id}:{market_type}`

**TTL Strategy**:
- **>2 hours before match**: 30 minutes
- **30 min - 2 hours before match**: 5 minutes
- **<30 minutes before match**: 2 minutes
- **Match in progress**: 1 minute
- **Match completed**: 24 hours (for historical lookups)

**Invalidation Triggers**:
- New odds data ingested for the match
- Model version updated
- Manual cache clear (admin action)

**Cache Entry Structure**:
```json
{
  "match_id": "uuid",
  "model_run_id": "uuid",
  "market": "moneyline",
  "probabilities": {
    "home_win": 0.45,
    "draw": 0.28,
    "away_win": 0.27
  },
  "expected_value": 0.08,
  "timestamp": "2025-10-15T14:30:00Z",
  "ttl": 300
}
```

**Performance Targets**:
- Cache hit rate: >80% during peak hours
- Cache read latency: <5ms (p95)
- Cache write latency: <10ms (p95)

---

### 2. Model Artifacts

**Cache Key Pattern**: `model:{model_id}:artifact`

**TTL**: 1-2 hours (refreshed on access)

**Strategy**:
- Models loaded into memory on first prediction request
- Models serialized to Redis for cross-service sharing
- LRU eviction when memory limits reached (keep 3 most recent models)

**Warming Strategy**:
- Pre-load active production models on service startup
- Background task refreshes model cache 30 minutes before expiry

**Cache Entry Structure**:
```json
{
  "model_id": "uuid",
  "version": "v2.3.1",
  "artifact_s3_path": "s3://bucket/models/...",
  "artifact_bytes": "<serialized model>",
  "metadata": {
    "feature_version": "v1.0",
    "framework": "xgboost",
    "size_bytes": 15728640
  },
  "loaded_at": "2025-10-15T14:00:00Z"
}
```

**Invalidation**:
- Explicit invalidation on model deployment
- Automatic eviction after TTL expires
- Manual purge via admin API

---

### 3. Feature Vectors

**Cache Key Pattern**: `features:{match_id}:{feature_version}`

**TTL**: 1 hour (pre-computed features), 5 minutes (real-time features)

**Strategy**:
- Pre-computed features (team form, H2H): Cached for 1 hour, updated daily
- Real-time features (odds, temporal): Cached for 5 minutes
- Combined feature vector cached after first computation

**Cache Entry Structure**:
```json
{
  "match_id": "uuid",
  "feature_version": "v1.0",
  "vector": [0.45, 0.23, 0.89, ...],  // 72 dimensions
  "feature_names": ["home_win_rate_last_5", ...],
  "computed_at": "2025-10-15T14:30:00Z",
  "ttl": 3600
}
```

**Invalidation**:
- Match data updated (score, status change)
- New odds snapshot ingested
- Feature version upgrade

---

### 4. Match & Odds Data

**Cache Key Pattern**: `match:{match_id}`, `odds:{match_id}:{provider}`

**TTL**:
- Match metadata: 1 hour (or until status change)
- Latest odds snapshot: 5 minutes
- Historical odds: 24 hours

**Strategy**:
- Cache latest odds snapshot per provider
- Cache aggregated odds summary (average across providers)
- Cache match list queries for common filters (today's matches, live matches)

**Cache Entry Structure**:
```json
{
  "match_id": "uuid",
  "home_team_id": "uuid",
  "away_team_id": "uuid",
  "start_at": "2025-10-15T18:00:00Z",
  "status": "scheduled",
  "latest_odds": {
    "provider_a": {"home": 1.85, "draw": 3.40, "away": 4.20},
    "provider_b": {"home": 1.90, "draw": 3.35, "away": 4.10}
  },
  "cached_at": "2025-10-15T14:30:00Z"
}
```

---

### 5. User Authentication Tokens

**Cache Key Pattern**: `auth:token:{token_hash}`

**TTL**: Token expiry time (typically 15 minutes for access tokens)

**Strategy**:
- Cache JWT verification results to avoid repeated signature validation
- Store user permissions for quick authorization checks
- Blacklist revoked tokens (TTL = original expiry)

**Cache Entry Structure**:
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "roles": ["premium_user"],
  "permissions": ["read:predictions", "read:matches"],
  "expires_at": "2025-10-15T15:00:00Z"
}
```

---

## Cache Warming Strategies

### Startup Warming
On service initialization:
1. Load active model artifacts into cache
2. Pre-compute features for upcoming matches (next 24 hours)
3. Cache today's match schedule
4. Load system configuration and metadata

### Scheduled Warming
Background tasks:
- **Every 5 minutes**: Refresh odds data cache for live matches
- **Every 15 minutes**: Pre-compute predictions for popular upcoming matches
- **Every 1 hour**: Refresh match list caches
- **Every 6 hours**: Refresh team statistics caches

### Predictive Warming
- Monitor access patterns to identify popular matches
- Pre-warm predictions for high-traffic matches 1 hour before kickoff
- Use ML model to predict which matches users will query

---

## Cache Invalidation

### Invalidation Patterns

| Event | Invalidate | Reason |
|-------|-----------|--------|
| New odds ingested | Match odds, predictions for that match | Stale odds data |
| Match status change | Match metadata, predictions | Status affects features |
| Model deployed | All predictions, model cache | New model version |
| User logout | Auth token cache entry | Security |
| Admin purge | Specified cache keys | Manual intervention |
| Feature version upgrade | All feature vectors | Breaking change |

### Invalidation Strategies

#### 1. Time-Based (TTL)
- Most common strategy
- Cache entries automatically expire
- Suitable for data with predictable freshness requirements

#### 2. Event-Based
- Invalidate on specific events (odds update, model deployment)
- Requires pub/sub or message queue (Redis Pub/Sub, RabbitMQ)
- More complex but ensures data freshness

#### 3. Write-Through
- Update cache immediately when database updated
- Guarantees consistency
- Used for critical data (auth tokens, model metadata)

#### 4. Lazy Invalidation
- Check data version/timestamp on cache read
- Refresh if stale
- Lower complexity, slight latency penalty on first read

### Implementation: Event-Driven Invalidation

```
Ingestion Service → [Data Updated] → Redis Pub/Sub
                                          ↓
                        ┌─────────────────┴─────────────────┐
                        ↓                                     ↓
                 Inference Service                      Feature Service
                 [Invalidate Caches]                   [Invalidate Caches]
```

**Redis Pub/Sub Channels**:
- `cache:invalidate:match:{match_id}`
- `cache:invalidate:model:{model_id}`
- `cache:invalidate:odds:{match_id}`
- `cache:invalidate:global` (purge all)

---

## Cache Configuration

### Redis Configuration

**Deployment**: Redis Cluster (3 master + 3 replica nodes)

**Memory**: 16 GB per node (48 GB total)

**Eviction Policy**: `allkeys-lru` (Least Recently Used)

**Persistence**:
- RDB snapshots every 5 minutes
- AOF (Append-Only File) enabled with `everysec` fsync

**Connection Pooling**:
- Min connections: 10
- Max connections: 100
- Connection timeout: 5 seconds

**Monitoring**:
- Track memory usage (alert at 80%)
- Monitor eviction rate (alert if >1000/sec)
- Track hit/miss ratio (alert if hit rate <70%)

### Application-Level Cache

**Implementation**: LRU Cache (per service instance)

**Size Limits**:
- Configuration cache: 100 MB
- Metadata cache: 50 MB
- Query result cache: 200 MB

**Use Cases**:
- System configuration (API keys, feature flags)
- Static data (sports, teams, venues)
- Frequently accessed metadata

---

## Monitoring & Observability

### Key Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Cache hit rate | >80% | <70% |
| Cache read latency (p95) | <5ms | >20ms |
| Cache write latency (p95) | <10ms | >50ms |
| Redis memory usage | <80% | >90% |
| Eviction rate | <100/sec | >1000/sec |
| Connection pool exhaustion | 0 | >5 events/min |

### Dashboards

**Grafana Dashboard: Cache Performance**
- Hit/miss ratio by cache type
- Latency histograms (read/write)
- Memory usage over time
- Eviction rate
- Top cache keys by access frequency

**Alerts**:
- Cache hit rate drops below 70%
- Redis memory usage exceeds 90%
- Cache latency p95 exceeds 50ms
- Redis connection failures
- Sudden spike in cache misses (>50% increase)

### Logging

**Log Cache Events**:
- Cache invalidation (with reason)
- Cache warming completion
- Eviction events (if frequent)
- Cache configuration changes

**Sample Log Entry**:
```json
{
  "timestamp": "2025-10-15T14:30:00Z",
  "level": "INFO",
  "event": "cache_invalidated",
  "cache_type": "prediction",
  "key": "prediction:abc123:model_v2:moneyline",
  "reason": "new_odds_ingested",
  "match_id": "abc123"
}
```

---

## Cache Failure Handling

### Failure Scenarios

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Redis cluster down | Cache unavailable | Fallback to database, circuit breaker |
| Redis node failure | Partial cache loss | Replica promotion, automatic failover |
| Cache stampede | Database overload | Cache locking, request coalescing |
| Stale data served | Incorrect predictions | TTL tuning, aggressive invalidation |
| Memory exhaustion | Evictions increase | Scale up, optimize cache size |

### Circuit Breaker Pattern

If Redis is unavailable:
1. Detect failure (3 consecutive timeouts)
2. Open circuit (skip cache, go direct to database)
3. Half-open after 30 seconds (test with single request)
4. Close circuit if successful

### Cache Stampede Prevention

**Problem**: When a popular cache entry expires, many concurrent requests trigger recalculation.

**Solution**: Cache locking pattern
```
1. Request arrives → Check cache
2. Cache miss → Acquire lock (Redis SETNX)
3. If lock acquired → Compute value, update cache, release lock
4. If lock not acquired → Wait 50-100ms, retry cache read
```

**Implementation**: Use Redis `SET key value NX PX milliseconds`

---

## Cost Optimization

### Strategies

1. **Selective Caching**: Don't cache low-value or infrequently accessed data
2. **Compression**: Compress large cache entries (feature vectors, models)
3. **Tiered TTLs**: Shorter TTLs for less critical data
4. **Cache Size Limits**: Set max size per cache key type
5. **Eviction Monitoring**: Track which data is evicted most (may not need caching)

### Cost Breakdown (Estimated)

| Component | Monthly Cost |
|-----------|--------------|
| Redis Cluster (3 nodes, 16 GB each) | $300 |
| Data transfer (egress) | $50 |
| Monitoring (CloudWatch/Datadog) | $30 |
| **Total** | **$380** |

---

## Testing Strategy

### Load Testing
- Simulate 1000 concurrent prediction requests
- Measure cache hit rate under load
- Verify performance degradation if Redis fails

### Cache Consistency Testing
- Verify invalidation triggers work correctly
- Test race conditions (concurrent updates)
- Validate TTL expiration behavior

### Failover Testing
- Kill Redis master node, verify replica promotion
- Test circuit breaker activation/deactivation
- Simulate cache stampede scenario

---

## Future Enhancements

### Planned Improvements
1. **Multi-Region Caching**: Deploy Redis clusters in multiple regions for global users
2. **CDN Integration**: Cache public API responses at edge locations
3. **Intelligent TTL**: Adjust TTL based on data volatility and access patterns
4. **Cache Analytics**: ML model to predict cache misses and optimize warming
5. **Distributed Locking**: Use Redlock algorithm for distributed cache locks

### Advanced Patterns
- **Read-Through Cache**: Automatically fetch from database on cache miss
- **Write-Behind Cache**: Asynchronously persist to database after cache update
- **Cache Aside with Bloom Filter**: Avoid cache queries for non-existent keys

---

**Last Updated**: 2025-10-15
**Version**: 1.0
**Status**: Phase 3 - Production Readiness
**Owner**: Backend Team
