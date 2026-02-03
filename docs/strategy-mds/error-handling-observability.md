# Error Handling & Observability Architecture

## Overview
This document defines the comprehensive error handling strategy and observability architecture for the Senzu AI system. Proper error handling and observability are critical for maintaining high availability (99.9% uptime) and quickly diagnosing issues in production.

---

## Error Handling Strategy

### Error Classification

#### 1. User Errors (4xx)
Caused by invalid client requests.

| Error Code | Error Type | Example | User Message | Retry? |
|------------|------------|---------|--------------|--------|
| 400 | Bad Request | Invalid match ID format | "Invalid request parameters" | No |
| 401 | Unauthorized | Missing/invalid auth token | "Authentication required" | No |
| 403 | Forbidden | Insufficient permissions | "Access denied" | No |
| 404 | Not Found | Match does not exist | "Resource not found" | No |
| 422 | Unprocessable Entity | Invalid filter parameters | "Invalid filter values" | No |
| 429 | Rate Limited | Too many requests | "Rate limit exceeded. Try again in X seconds" | Yes (after delay) |

#### 2. Server Errors (5xx)
Caused by system failures.

| Error Code | Error Type | Example | User Message | Retry? | Alert? |
|------------|------------|---------|--------------|--------|--------|
| 500 | Internal Server Error | Unhandled exception | "An error occurred. Please try again" | Yes | Yes |
| 502 | Bad Gateway | Downstream service unavailable | "Service temporarily unavailable" | Yes | Yes |
| 503 | Service Unavailable | Database down, circuit open | "Service temporarily unavailable" | Yes | Yes |
| 504 | Gateway Timeout | Prediction took >30s | "Request timed out. Please try again" | Yes | Yes |

#### 3. Dependency Errors
Errors from external services.

| Dependency | Error Scenario | Handling Strategy | Fallback |
|------------|----------------|-------------------|----------|
| PostgreSQL | Connection timeout | Retry with exponential backoff (3 attempts) | Circuit breaker |
| Redis | Unavailable | Skip cache, go direct to DB | Circuit breaker |
| S3 | Model artifact not found | Load previous model version | Alert |
| Sports Data Provider | API rate limit | Queue request, retry after delay | Use cached data |
| Model Service | Inference timeout | Retry once, then fail gracefully | Return cached prediction |

---

## Error Response Format

### Standard Error Response

All API errors follow this JSON structure:

```json
{
  "error": {
    "code": "PREDICTION_GENERATION_FAILED",
    "message": "Unable to generate prediction for this match",
    "details": "Model inference timed out after 10 seconds",
    "timestamp": "2025-10-15T14:30:00Z",
    "request_id": "req_abc123xyz",
    "documentation_url": "https://docs.senzu-ai.com/errors/prediction-failed"
  }
}
```

### Error Code Taxonomy

**Format**: `{DOMAIN}_{ERROR_TYPE}_{DETAIL}`

**Examples**:
- `AUTH_TOKEN_EXPIRED`
- `MATCH_NOT_FOUND`
- `PREDICTION_GENERATION_FAILED`
- `FEATURE_COMPUTATION_TIMEOUT`
- `MODEL_LOADING_FAILED`
- `ODDS_DATA_UNAVAILABLE`
- `DATABASE_CONNECTION_FAILED`
- `RATE_LIMIT_EXCEEDED`

### Detailed Error Context (Internal Logging)

Internal logs include additional context not exposed to users:

```json
{
  "error": {
    "code": "MODEL_LOADING_FAILED",
    "message": "Failed to load model artifact",
    "stack_trace": "...",
    "context": {
      "model_id": "model_abc123",
      "s3_path": "s3://bucket/models/model_abc123.pkl",
      "exception": "botocore.exceptions.ClientError: NoSuchKey"
    },
    "user_id": "user_xyz789",
    "request_id": "req_abc123xyz",
    "service": "model-service",
    "timestamp": "2025-10-15T14:30:00Z"
  }
}
```

---

## Retry & Backoff Strategies

### Exponential Backoff

**Formula**: `delay = base_delay * (2 ^ attempt) + random_jitter`

**Configuration**:
- Base delay: 100ms
- Max attempts: 3
- Max delay: 5 seconds
- Jitter: ±25% (prevents thundering herd)

**Example Timeline**:
- Attempt 1: Immediate
- Attempt 2: 100ms + jitter (75-125ms)
- Attempt 3: 200ms + jitter (150-250ms)
- Attempt 4: 400ms + jitter (300-500ms)

### Retry Decision Matrix

| Error Type | Retry? | Max Attempts | Backoff |
|------------|--------|--------------|---------|
| Network timeout | Yes | 3 | Exponential |
| Database deadlock | Yes | 3 | Exponential |
| Rate limit (429) | Yes | 5 | Linear (wait per Retry-After header) |
| Auth failure (401) | No | 0 | N/A |
| Not found (404) | No | 0 | N/A |
| Bad request (400) | No | 0 | N/A |
| Model inference error | Yes | 1 | None (immediate) |

### Circuit Breaker Pattern

Prevents cascading failures when a dependency is consistently failing.

**States**:
1. **Closed**: Normal operation, requests flow through
2. **Open**: Dependency failing, requests fail immediately
3. **Half-Open**: Testing if dependency recovered

**Thresholds**:
- Open circuit: 5 consecutive failures or 50% failure rate over 10 requests
- Half-open test: After 30 seconds
- Close circuit: 3 consecutive successful requests

**Implementation** (per dependency):
- PostgreSQL circuit breaker
- Redis circuit breaker
- Model Service circuit breaker
- Sports Data Provider circuit breaker

---

## Timeout Configuration

### Service-Level Timeouts

| Service | Operation | Timeout | Reasoning |
|---------|-----------|---------|-----------|
| API Gateway | Total request | 30s | Max acceptable user wait time |
| Auth Service | Token verification | 1s | Fast auth check |
| Inference Service | Prediction generation | 10s | Includes feature + inference |
| Feature Service | Feature computation | 3s | Most features pre-computed |
| Model Service | Model inference | 5s | XGBoost inference |
| Data Ingestion | API fetch | 15s | External API may be slow |

### Database Timeouts

- **Connection timeout**: 5s
- **Query timeout**: 10s (most queries <100ms)
- **Transaction timeout**: 30s
- **Connection pool acquire timeout**: 2s

### External API Timeouts

- **Sports Data Provider**: 15s
- **S3 GET operation**: 10s
- **Redis operation**: 500ms

---

## Logging Strategy

### Log Levels

| Level | Use Case | Example | Volume |
|-------|----------|---------|--------|
| **ERROR** | Unrecoverable failures, system errors | Database connection failed, unhandled exception | Low |
| **WARN** | Recoverable issues, degraded performance | Cache miss rate >50%, retry triggered | Medium |
| **INFO** | Key business events | User registered, prediction generated | Medium |
| **DEBUG** | Detailed flow information | Feature values, model inputs | High (dev only) |
| **TRACE** | Very detailed debugging | SQL queries, HTTP requests | Very High (dev only) |

### Structured Logging Format

**Standard**: JSON logs with consistent schema

```json
{
  "timestamp": "2025-10-15T14:30:00.123Z",
  "level": "ERROR",
  "service": "inference-service",
  "version": "v1.2.3",
  "environment": "production",
  "request_id": "req_abc123xyz",
  "user_id": "user_xyz789",
  "message": "Failed to generate prediction",
  "error": {
    "code": "MODEL_INFERENCE_TIMEOUT",
    "stack_trace": "..."
  },
  "context": {
    "match_id": "match_abc123",
    "model_id": "model_v2.3",
    "duration_ms": 10234
  }
}
```

### Log Aggregation

**Technology**: ELK Stack (Elasticsearch, Logstash, Kibana) or CloudWatch Logs

**Retention**:
- ERROR logs: 90 days
- WARN logs: 30 days
- INFO logs: 14 days
- DEBUG logs: 3 days (dev environment only)

### Sensitive Data Redaction

**Automatically redact**:
- Passwords, API keys
- Full email addresses (keep domain: `user@******.com`)
- JWT tokens
- Credit card numbers

**Implementation**: Regex-based redaction in logging middleware

---

## Observability Architecture

### Three Pillars of Observability

1. **Metrics**: Quantitative measurements (latency, throughput, error rate)
2. **Logs**: Discrete event records (errors, warnings, business events)
3. **Traces**: Request flow across services (distributed tracing)

---

## Metrics & Monitoring

### Key Metrics to Track

#### Application Metrics

| Metric | Type | Description | Alert Threshold |
|--------|------|-------------|-----------------|
| `api.requests.total` | Counter | Total API requests | N/A |
| `api.requests.duration` | Histogram | Request latency | p95 >500ms |
| `api.requests.errors` | Counter | Failed requests | Error rate >1% |
| `predictions.generated` | Counter | Predictions created | N/A |
| `predictions.cache_hit_rate` | Gauge | Cache effectiveness | <70% |
| `models.inference_duration` | Histogram | Model inference time | p95 >200ms |
| `features.computation_duration` | Histogram | Feature build time | p95 >100ms |
| `database.query_duration` | Histogram | DB query time | p95 >50ms |
| `database.connections.active` | Gauge | Active DB connections | >80 (pool size 100) |

#### Infrastructure Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `cpu.usage` | CPU utilization | >80% |
| `memory.usage` | Memory utilization | >85% |
| `disk.usage` | Disk space used | >80% |
| `network.throughput` | Network I/O | N/A (baseline) |
| `redis.memory_usage` | Redis memory | >90% |
| `postgresql.connections` | DB connections | >90% of max |

#### Business Metrics

| Metric | Description | Purpose |
|--------|-------------|---------|
| `users.active_daily` | Daily active users | Growth tracking |
| `predictions.by_sport` | Predictions per sport | Product insights |
| `predictions.high_ev_count` | High EV predictions (>5%) | Quality metric |
| `api.requests.by_endpoint` | Traffic per endpoint | Capacity planning |

### Monitoring Stack

**Technology**: DataDog (Unified Observability Platform)

**Components**:
- **DataDog Agent**: Metrics, logs, and trace collection
- **DataDog APM**: Application Performance Monitoring with distributed tracing
- **DataDog Logs**: Centralized log management
- **DataDog Monitors**: Alerting and anomaly detection
- **DataDog Dashboards**: Pre-built and custom visualizations

**Why DataDog**:
- Unified platform for metrics, logs, traces, and APM
- Much faster setup than open-source stack (hours vs days)
- Automatic instrumentation for Python/FastAPI
- Excellent out-of-box dashboards and service maps
- Cost-effective for small teams (~$100-200/month for 5-10 hosts)
- Reduces operational overhead
- Built-in anomaly detection using ML
- Strong PagerDuty integration

**Deployment**:
- DataDog Agent runs as container sidecar or daemon
- `ddtrace` Python SDK for automatic instrumentation
- Metrics sent every 15 seconds
- Logs streamed in real-time
- 15-month metric retention (configurable)

### DataDog Setup & Configuration

#### 1. Installation (Python Services)

**Install Dependencies**:
```bash
pip install ddtrace datadog
```

**requirements.txt**:
```
ddtrace>=2.0.0
datadog>=0.47.0
```

#### 2. Automatic Instrumentation

**Run with automatic instrumentation** (recommended for FastAPI):
```bash
DD_SERVICE=inference-service \
DD_ENV=production \
DD_VERSION=1.2.3 \
DD_AGENT_HOST=datadog-agent \
DD_LOGS_INJECTION=true \
DD_TRACE_ANALYTICS_ENABLED=true \
ddtrace-run python -m uvicorn main:app --host 0.0.0.0 --port 8080
```

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

# Install DataDog tracer
RUN pip install ddtrace

# Copy application
COPY . /app
WORKDIR /app

# Run with automatic instrumentation
CMD ["ddtrace-run", "python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### 3. Manual Instrumentation (Optional)

**main.py**:
```python
from ddtrace import tracer, patch_all
from ddtrace.contrib.logging import patch as patch_logging
import logging

# Patch all supported libraries
patch_all()

# Enable log correlation (adds trace_id, span_id to logs)
patch_logging()

# Configure tracer
tracer.configure(
    hostname="datadog-agent",
    port=8126,
)

# Custom metrics
from datadog import statsd
statsd.increment("predictions.generated")
statsd.histogram("features.computation_duration", 85.2)  # ms
statsd.gauge("predictions.cache_hit_rate", 0.82)
```

#### 4. DataDog Agent Deployment

**docker-compose.yml** (for local development):
```yaml
version: '3.8'

services:
  datadog-agent:
    image: datadog/agent:latest
    environment:
      - DD_API_KEY=${DD_API_KEY}
      - DD_SITE=datadoghq.com  # or datadoghq.eu
      - DD_APM_ENABLED=true
      - DD_LOGS_ENABLED=true
      - DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL=true
      - DD_DOGSTATSD_NON_LOCAL_TRAFFIC=true
    ports:
      - "8126:8126"  # APM traces
      - "8125:8125/udp"  # DogStatsD metrics
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /proc/:/host/proc/:ro
      - /sys/fs/cgroup/:/host/sys/fs/cgroup:ro

  inference-service:
    build: ./services/inference-service
    environment:
      - DD_AGENT_HOST=datadog-agent
      - DD_SERVICE=inference-service
      - DD_ENV=development
    depends_on:
      - datadog-agent
```

**Kubernetes DaemonSet** (for production):
```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: datadog-agent
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: datadog-agent
  template:
    metadata:
      labels:
        app: datadog-agent
    spec:
      serviceAccountName: datadog-agent
      containers:
      - name: datadog-agent
        image: datadog/agent:latest
        env:
        - name: DD_API_KEY
          valueFrom:
            secretKeyRef:
              name: datadog-secret
              key: api-key
        - name: DD_SITE
          value: "datadoghq.com"
        - name: DD_APM_ENABLED
          value: "true"
        - name: DD_LOGS_ENABLED
          value: "true"
        - name: DD_KUBERNETES_KUBELET_HOST
          valueFrom:
            fieldRef:
              fieldPath: status.hostIP
        ports:
        - containerPort: 8125
          name: dogstatsdport
          protocol: UDP
        - containerPort: 8126
          name: traceport
          protocol: TCP
        volumeMounts:
        - name: dockersocket
          mountPath: /var/run/docker.sock
        - name: procdir
          mountPath: /host/proc
          readOnly: true
        - name: cgroups
          mountPath: /host/sys/fs/cgroup
          readOnly: true
      volumes:
      - name: dockersocket
        hostPath:
          path: /var/run/docker.sock
      - name: procdir
        hostPath:
          path: /proc
      - name: cgroups
        hostPath:
          path: /sys/fs/cgroup
```

#### 5. Log Configuration

**Structured JSON Logging** (required for DataDog log parsing):
```python
import logging
import json_logging

# Configure JSON logging
json_logging.init_fastapi(enable_json=True)
json_logging.init_request_instrument(app)

# Logging with trace correlation (automatic with ddtrace)
logger = logging.getLogger(__name__)
logger.info("Processing prediction", extra={
    "match_id": match_id,
    "model_id": model_id,
    "user_id": user_id
})
```

**Log Attributes** (automatically added by ddtrace):
- `dd.trace_id`: Trace ID for correlation
- `dd.span_id`: Span ID
- `dd.service`: Service name
- `dd.env`: Environment (dev, staging, prod)
- `dd.version`: Application version

#### 6. Custom Metrics

**StatsD-style metrics**:
```python
from datadog import statsd

# Counter
statsd.increment("predictions.generated", tags=["sport:soccer", "model:v2.3"])

# Gauge
statsd.gauge("database.connections.active", 45)

# Histogram (for percentiles)
statsd.histogram("model.inference_duration", 123.4, tags=["model:xgboost"])

# Timing (convenience method for histograms)
with statsd.timed("feature.computation_time"):
    features = compute_features(match)
```

#### 7. Cost Estimation

**DataDog Pricing** (approximate, as of 2026):
| Component | Cost | Notes |
|-----------|------|-------|
| Infrastructure Monitoring | $15/host/month | Base metrics and monitoring |
| APM & Continuous Profiler | $31/host/month | Application performance monitoring |
| Log Management | $0.10/GB ingested | Depends on log volume |
| **Total (5 hosts)** | **~$230/month** | $46/host * 5 hosts |
| **Total (10 hosts)** | **~$460/month** | Scales linearly |

**Cost Optimization**:
- Use log sampling for high-volume logs
- Set retention policies (keep only 15 days)
- Use exclusion filters to drop noisy logs
- APM trace sampling (default is intelligent)

### Dashboards

#### 1. System Health Dashboard
- Overall request rate (RPS)
- Overall error rate (%)
- p50, p95, p99 latency
- Service status (up/down)
- Cache hit rates

#### 2. Service Deep-Dive Dashboard (per service)
- Request rate
- Error rate
- Latency distribution
- Dependency call success rate
- Resource utilization (CPU, memory)

#### 3. Database Dashboard
- Query throughput (queries/sec)
- Query latency (p50, p95, p99)
- Connection pool usage
- Slow queries (>1s)
- Disk I/O

#### 4. Business Metrics Dashboard
- Predictions generated (per hour)
- Users active (DAU/MAU)
- High-EV predictions
- Top sports/leagues by volume

---

## Alerting Strategy

### Alert Severity Levels

| Severity | Response Time | Notification | Example |
|----------|---------------|--------------|---------|
| **Critical** | Immediate | PagerDuty (on-call) | API down, database unreachable |
| **High** | 15 minutes | Slack + Email | Error rate >5%, latency >1s |
| **Medium** | 1 hour | Slack | Cache hit rate <70%, slow queries |
| **Low** | 4 hours | Email only | Non-critical warnings |

### Alert Rules

**Note**: Alerts are configured in DataDog Monitors UI or via Terraform/API. Examples below show the logical conditions.

#### Critical Alerts

**API Gateway Down**
- **Metric**: `aws.ecs.service.running` or container health check
- **Condition**: `< 1` for 1 minute
- **Severity**: Critical
- **Notification**: PagerDuty (immediate phone/SMS)
- **Message**: "API Gateway is down for 1 minute - @pagerduty-critical"

**Database Unreachable**
- **Metric**: `postgresql.database.count` or health check
- **Condition**: No data for 2 minutes
- **Severity**: Critical
- **Notification**: PagerDuty
- **Message**: "PostgreSQL is unreachable - @pagerduty-critical"

**High Error Rate**
- **Metric**: `trace.flask.request.errors` or `api.requests.errors`
- **Condition**: `> 5%` of requests for 5 minutes
- **Severity**: Critical
- **Notification**: PagerDuty
- **Message**: "Error rate >5% for 5 minutes - @pagerduty-critical"

#### High Alerts

**High Latency**
- **Metric**: `trace.flask.request.duration.by.resource_service.95percentile`
- **Condition**: `> 1 second` for 10 minutes
- **Severity**: High
- **Notification**: Slack + Email
- **Message**: "p95 latency >1s for 10 minutes - @slack-alerts @oncall"

**Redis Memory High**
- **Metric**: `redis.mem.used / redis.mem.maxmemory`
- **Condition**: `> 0.9` for 5 minutes
- **Severity**: High
- **Notification**: Slack
- **Message**: "Redis memory usage >90% - @slack-database"

#### Medium Alerts

**Low Cache Hit Rate**
- **Metric**: `predictions.cache_hit_rate` (custom metric)
- **Condition**: `< 0.7` for 30 minutes
- **Severity**: Medium
- **Notification**: Slack
- **Message**: "Prediction cache hit rate <70% for 30 minutes - @slack-alerts"

**Slow Database Queries**
- **Metric**: `postgresql.query_duration.95percentile`
- **Condition**: `> 500ms` for 15 minutes
- **Severity**: Medium
- **Notification**: Slack
- **Message**: "Database query p95 >500ms - @slack-database"

**Anomaly Detection (DataDog ML)**
- **Metric**: Any key metric
- **Condition**: DataDog's anomaly detection algorithm
- **Severity**: Medium
- **Notification**: Slack
- **Message**: "Anomalous behavior detected in {metric_name}"

### Alert Routing

**PagerDuty Integration**:
- Critical alerts → On-call engineer (immediate phone/SMS)
- High alerts → On-call engineer (push notification)

**Slack Integration**:
- High/Medium alerts → `#alerts` channel
- Database alerts → `#database-team` channel
- Model alerts → `#ml-team` channel

**Alert Fatigue Prevention**:
- Group similar alerts (e.g., multiple service instances down)
- Silence known issues during maintenance windows
- Automatically close alerts when condition resolves
- Weekly review of alert noise (false positives)

---

## Distributed Tracing

### Technology

**DataDog APM** (Application Performance Monitoring with distributed tracing)

**Why DataDog APM**:
- Automatic instrumentation with `ddtrace-run` command
- No manual span creation needed for common frameworks (FastAPI, Flask)
- Built-in service maps showing dependencies
- Request traces correlated with logs automatically
- Performance profiling and flame graphs
- No separate tracing infrastructure to manage

### Trace Context Propagation

**DataDog Headers**:
- `x-datadog-trace-id`: Unique trace identifier (64-bit integer)
- `x-datadog-parent-id`: Parent span identifier
- `x-datadog-sampling-priority`: Sampling decision (0=drop, 1=keep)
- `x-datadog-tags`: Additional trace tags

**Propagation**: `ddtrace` automatically propagates trace context via HTTP headers across services

**Automatic Instrumentation**:
```python
# Install: pip install ddtrace
# Run with automatic instrumentation:
# ddtrace-run python -m uvicorn main:app

# Manual instrumentation (if needed):
from ddtrace import tracer, patch_all
patch_all()  # Auto-instrument common libraries

# Custom spans:
with tracer.trace("custom_operation", service="inference-service") as span:
    span.set_tag("match_id", match_id)
    # ... your code
```

### Trace Structure

```
Trace: Prediction Request (trace_id: abc123)
├─ Span: API Gateway (200ms)
│  ├─ Span: Auth Verification (50ms)
│  └─ Span: Route to Inference Service (5ms)
├─ Span: Inference Service (180ms)
│  ├─ Span: Feature Service Call (80ms)
│  │  ├─ Span: Database Query - Match Data (30ms)
│  │  ├─ Span: Database Query - Team Stats (25ms)
│  │  └─ Span: Feature Computation (20ms)
│  ├─ Span: Model Service Call (90ms)
│  │  ├─ Span: Load Model from Cache (10ms)
│  │  └─ Span: Model Inference (75ms)
│  └─ Span: Save Prediction to DB (10ms)
└─ Span: Response Serialization (20ms)
```

### Span Attributes

**Standard Attributes**:
- `service.name`: "inference-service"
- `http.method`: "GET"
- `http.url`: "/matches/abc123/predictions"
- `http.status_code`: 200
- `error`: true/false

**Custom Attributes**:
- `match_id`: "abc123"
- `model_id`: "model_v2.3"
- `cache_hit`: true/false
- `feature_version`: "v1.0"

### Sampling Strategy

DataDog APM uses intelligent sampling to balance observability with cost:

- **Default Sampling**: 100% of first 10 req/sec per service, then adaptive sampling
- **Error Traces**: 100% sampling (always trace errors)
- **Custom Priority Sampling**: Configure via `ddtrace`
  ```python
  from ddtrace import tracer
  from ddtrace.constants import SAMPLING_PRIORITY_KEY

  # Force trace high-value requests
  if expected_value > 0.1:
      span.context.sampling_priority = 2  # USER_KEEP
  ```

**Cost Management**:
- APM pricing: ~$31-40/host/month for full APM
- Lower sampling rate if costs become concern
- Use trace retention filters to keep only important traces

---

## Health Checks

### Endpoint: `GET /health`

**Response** (healthy):
```json
{
  "status": "healthy",
  "timestamp": "2025-10-15T14:30:00Z",
  "version": "v1.2.3",
  "uptime_seconds": 86400,
  "dependencies": {
    "database": "healthy",
    "redis": "healthy",
    "model_service": "healthy",
    "feature_service": "healthy"
  }
}
```

**Response** (unhealthy):
```json
{
  "status": "unhealthy",
  "timestamp": "2025-10-15T14:30:00Z",
  "version": "v1.2.3",
  "dependencies": {
    "database": "unhealthy",
    "redis": "healthy",
    "model_service": "degraded"
  }
}
```

### Health Check Types

| Type | Endpoint | Check | Frequency |
|------|----------|-------|-----------|
| **Liveness** | `/health/live` | Service process running | Every 5s (Kubernetes) |
| **Readiness** | `/health/ready` | Ready to handle requests (DB connected) | Every 10s |
| **Startup** | `/health/startup` | Service initialization complete | Once at startup |

### Dependency Health Checks

Each service checks its dependencies:
- **Database**: Execute `SELECT 1` query
- **Redis**: Execute `PING` command
- **S3**: Check access to bucket (optional)
- **Model Service**: Check model loaded

---

## Incident Response

### Incident Severity Levels

| Level | Definition | Response | Example |
|-------|------------|----------|---------|
| **P0** | Critical outage | All hands on deck, immediate response | API completely down |
| **P1** | Major degradation | On-call responds within 15 min | Error rate >10% |
| **P2** | Partial degradation | Respond within 1 hour | Single service slow |
| **P3** | Minor issue | Respond within 4 hours | Low cache hit rate |

### Runbooks

**Location**: `docs/runbooks/`

**Runbook Structure**:
1. **Symptoms**: How to recognize the issue
2. **Diagnosis**: How to confirm root cause
3. **Resolution**: Step-by-step fix
4. **Prevention**: How to avoid in future

**Example Runbooks**:
- `database-connection-failure.md`
- `high-latency-investigation.md`
- `model-inference-failure.md`
- `cache-invalidation-issues.md`

### Post-Incident Review

After every P0/P1 incident:
1. **Write incident report** (within 48 hours)
2. **Conduct blameless postmortem**
3. **Identify action items** (preventive measures)
4. **Update runbooks**

---

## Error Budget

### SLO (Service Level Objectives)

| Metric | Target | Error Budget (Monthly) |
|--------|--------|------------------------|
| API Availability | 99.9% | 43 minutes downtime |
| Request Success Rate | 99.5% | 0.5% error rate |
| p95 Latency | <500ms | 5% of requests >500ms |

### Error Budget Policy

- **Budget not exhausted**: Continue feature releases
- **Budget 50% consumed**: Slow down releases, focus on reliability
- **Budget exhausted**: Feature freeze, reliability work only

---

## Future Enhancements

1. **Anomaly Detection**: ML-based detection of unusual patterns
2. **Automated Remediation**: Auto-restart services, scale resources
3. **Chaos Engineering**: Regular failure injection tests
4. **Advanced Tracing**: Tail-based sampling, trace analytics
5. **Real User Monitoring (RUM)**: Frontend performance tracking

---

**Last Updated**: 2025-10-15
**Version**: 1.0
**Status**: Phase 3 - Production Readiness
**Owner**: Backend Team, SRE Team
