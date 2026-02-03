# Security Architecture Documentation

## Overview
This document defines the comprehensive security architecture for the Senzu AI system, covering authentication, authorization, data protection, network security, and compliance considerations.

---

## Security Principles

### Core Tenets

1. **Defense in Depth**: Multiple layers of security controls
2. **Least Privilege**: Minimal permissions required for operation
3. **Zero Trust**: Verify every request, never assume trust
4. **Secure by Default**: Security built-in, not bolted-on
5. **Privacy by Design**: Protect user data at every stage

### Threat Model

| Threat | Risk Level | Mitigation |
|--------|------------|------------|
| Unauthorized API access | High | JWT authentication, rate limiting |
| Data breach (user data) | High | Encryption at rest/transit, access controls |
| SQL injection | Medium | Parameterized queries, ORM usage |
| DDoS attack | Medium | Rate limiting, CDN, auto-scaling |
| Model theft/poisoning | Medium | Access controls, model versioning |
| Credential stuffing | Medium | Password policies, MFA, rate limiting |
| Man-in-the-Middle (MITM) | Low | HTTPS/TLS only, certificate pinning |
| Insider threat | Low | Audit logging, RBAC, separation of duties |

---

## Authentication & Authorization

### Authentication Strategy

**Primary Method**: JWT (JSON Web Tokens)

**Token Types**:
1. **Access Token**: Short-lived (15 minutes), used for API requests
2. **Refresh Token**: Long-lived (30 days), used to obtain new access tokens

**Token Structure** (JWT):
```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_id_abc123",
    "email": "user@example.com",
    "roles": ["premium_user"],
    "iat": 1697390000,
    "exp": 1697390900,
    "iss": "https://api.senzu-ai.com",
    "aud": "senzu-ai-app"
  },
  "signature": "..."
}
```

**Signing Algorithm**: RS256 (RSA + SHA-256)
- Private key: Stored in AWS Secrets Manager / HashiCorp Vault
- Public key: Distributed to all services for verification
- Key rotation: Every 90 days

### Authentication Flow

#### 1. User Registration

```
User → POST /auth/register
       {email, password}
           ↓
    [Validate email format]
    [Check email uniqueness]
    [Hash password (bcrypt, cost=12)]
    [Create user record]
           ↓
    Return 201 Created
    {user_id, message: "Verify email"}
```

**Password Requirements**:
- Minimum 8 characters
- At least 1 uppercase, 1 lowercase, 1 digit, 1 special character
- Not in common password list (10k most common)
- Password strength: zxcvbn score ≥3

#### 2. User Login

```
User → POST /auth/login
       {email, password}
           ↓
    [Fetch user by email]
    [Verify password hash]
    [Check account status (active/suspended)]
    [Rate limit: 5 attempts per 15 min]
           ↓
    Generate access token (15 min TTL)
    Generate refresh token (30 day TTL)
    Store refresh token in DB
           ↓
    Return 200 OK
    {
      access_token: "...",
      refresh_token: "...",
      expires_in: 900
    }
```

**Failed Login Protection**:
- Rate limiting: Max 5 attempts per 15 minutes per IP
- Account lockout: After 10 failed attempts in 1 hour
- Notification: Email user about failed login attempts

#### 3. Token Refresh

```
User → POST /auth/refresh
       {refresh_token}
           ↓
    [Validate refresh token signature]
    [Check token not revoked (blacklist)]
    [Check token not expired]
    [Verify user account still active]
           ↓
    Generate new access token
    (Optional) Rotate refresh token
           ↓
    Return 200 OK
    {
      access_token: "...",
      expires_in: 900
    }
```

#### 4. Logout

```
User → POST /auth/logout
       {refresh_token}
           ↓
    [Add refresh token to blacklist]
    [Delete token from DB]
           ↓
    Return 204 No Content
```

**Token Blacklist**:
- Store revoked tokens in Redis (TTL = original expiry time)
- Check blacklist on every token refresh
- Automatically clean expired entries

---

### Authorization (RBAC - Role-Based Access Control)

#### User Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| **Free User** | Basic access | Read predictions (10/day), view matches |
| **Premium User** | Paid subscriber | Read predictions (unlimited), API access |
| **Admin** | Internal user | All read/write, user management |
| **ML Engineer** | Model team | Model deployment, evaluation metrics |

#### Permission Model

**Format**: `<action>:<resource>`

**Examples**:
- `read:predictions`
- `read:matches`
- `write:models`
- `delete:users`
- `read:analytics`

#### Role-Permission Matrix

| Permission | Free User | Premium User | Admin | ML Engineer |
|------------|-----------|--------------|-------|-------------|
| `read:predictions` | ✓ (10/day) | ✓ (unlimited) | ✓ | ✓ |
| `read:matches` | ✓ | ✓ | ✓ | ✓ |
| `read:odds` | ✓ | ✓ | ✓ | ✓ |
| `read:models` | ✗ | ✗ | ✓ | ✓ |
| `write:models` | ✗ | ✗ | ✓ | ✓ |
| `read:users` | ✗ | ✗ | ✓ | ✗ |
| `write:users` | ✗ | ✗ | ✓ | ✗ |
| `read:analytics` | ✗ | ✗ | ✓ | ✓ |

#### Authorization Middleware

```
Request → API Gateway
    ↓
[Extract JWT from Authorization header]
[Verify JWT signature]
[Check token not expired]
[Check token not blacklisted]
[Extract user roles from token]
    ↓
[Check required permission for endpoint]
[Verify user has permission]
    ↓
Allow request OR Return 403 Forbidden
```

---

## API Security

### Rate Limiting

**Strategy**: Token bucket algorithm

**Limits by Role**:
| Role | Rate Limit | Burst |
|------|------------|-------|
| Anonymous | 10 req/min | 20 |
| Free User | 60 req/min | 100 |
| Premium User | 600 req/min | 1000 |
| Admin | Unlimited | N/A |

**Implementation**: Redis-based counter

**Response Headers**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1697390900
```

**Rate Limit Exceeded Response**:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 30 seconds.",
    "retry_after": 30
  }
}
```

### Input Validation

**Validation Rules**:
1. **Schema Validation**: Use JSON Schema or Pydantic models
2. **Type Checking**: Ensure correct data types
3. **Range Validation**: Min/max values for numbers
4. **Length Limits**: Max string/array lengths
5. **Format Validation**: Email, UUID, date formats
6. **Whitelist Validation**: Enum values, allowed characters

**Example Validation** (Match ID):
```python
# Invalid inputs rejected:
match_id = "abc'; DROP TABLE matches; --"  # SQL injection attempt
match_id = "../../../etc/passwd"          # Path traversal
match_id = "a" * 10000                    # DoS via large input

# Valid format:
match_id = "550e8400-e29b-41d4-a716-446655440000"  # UUID v4
```

**Sanitization**:
- HTML encode user-generated content
- Strip dangerous characters from inputs
- Normalize Unicode strings (NFC form)

### CORS (Cross-Origin Resource Sharing)

**Configuration**:
```
Access-Control-Allow-Origin: https://senzu-ai.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Authorization, Content-Type
Access-Control-Max-Age: 86400
Access-Control-Allow-Credentials: true
```

**Policy**: Whitelist specific origins (not `*`)

### HTTPS/TLS

**Requirements**:
- **TLS 1.2+** required (TLS 1.3 preferred)
- **Disable TLS 1.0/1.1** (deprecated, insecure)
- **Strong cipher suites only**: ECDHE-RSA-AES256-GCM-SHA384, etc.
- **HSTS (HTTP Strict Transport Security)**: Enforce HTTPS
  - Header: `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`

**Certificate Management**:
- Use Let's Encrypt or AWS Certificate Manager
- Auto-renewal 30 days before expiry
- Monitor certificate expiration (alert at 14 days)

### Content Security Policy (CSP)

**Header**:
```
Content-Security-Policy:
  default-src 'self';
  script-src 'self';
  style-src 'self';
  img-src 'self' data:;
  font-src 'self';
  connect-src 'self' https://api.senzu-ai.com;
```

**Purpose**: Prevent XSS attacks by controlling resource loading

---

## Data Security

### Encryption at Rest

**Database Encryption**:
- **PostgreSQL**: Enable transparent data encryption (TDE)
  - AWS RDS: Enable encryption at volume level (AES-256)
  - Encrypt automated backups
- **Redis**: Enable encryption at rest (AWS ElastiCache)

**Sensitive Fields**:
| Field | Encryption Method |
|-------|-------------------|
| Password | bcrypt (cost factor 12) |
| API Keys | AES-256-GCM (per-user key) |
| Refresh Tokens | SHA-256 hash (store hash only) |
| Payment Info | Tokenized (Stripe, not stored) |

**S3 Encryption**:
- Enable S3 bucket encryption (SSE-S3 or SSE-KMS)
- Encrypt model artifacts before upload
- Use pre-signed URLs for limited-time access

### Encryption in Transit

**Requirements**:
- All API communication: HTTPS only (redirect HTTP → HTTPS)
- Database connections: SSL/TLS required
- Redis connections: TLS enabled (if on public network)
- Internal service-to-service: mTLS (mutual TLS)

**mTLS (Mutual TLS) for Microservices**:
- Each service has its own certificate
- Services verify each other's identity
- Certificate rotation: Every 30 days
- Implementation: Istio service mesh or AWS App Mesh

### Data Masking & Redaction

**PII (Personally Identifiable Information)**:
- Mask in logs: `user@******.com` (keep domain)
- Mask API keys: `sk_prod_************abcd` (show last 4 chars)
- Redact passwords: Never log passwords

**Audit Logs**: Retain full data (for compliance)

### Backup Security

**Database Backups**:
- Automated daily backups (RDS snapshots)
- Encrypted backups (AES-256)
- 30-day retention
- Store in separate AWS region (disaster recovery)
- Test restore process monthly

**Backup Access**:
- Restricted to admin role only
- Audit all backup access attempts
- MFA required for restore operations

---

## Network Security

### Network Architecture

```
                  Internet
                     │
              ┌──────▼──────┐
              │   CloudFront/CDN   │
              │   (DDoS Protection) │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │   WAF        │
              │ (Firewall)   │
              └──────┬──────┘
                     │
         ┌───────────▼───────────┐
         │   Load Balancer        │
         │   (Public Subnet)      │
         └───────────┬───────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
┌────▼────┐    ┌────▼────┐    ┌────▼────┐
│  API    │    │  API    │    │  API    │
│ Gateway │    │ Gateway │    │ Gateway │
│  (VPC)  │    │  (VPC)  │    │  (VPC)  │
└────┬────┘    └────┬────┘    └────┬────┘
     │               │               │
     └───────────────┼───────────────┘
                     │ (Private Subnet)
     ┌───────────────┼───────────────┐
     │               │               │
┌────▼────┐    ┌────▼────┐    ┌────▼────┐
│Inference│    │Feature  │    │  Model  │
│ Service │    │ Service │    │ Service │
└────┬────┘    └────┬────┘    └────┬────┘
     │               │               │
     └───────────────┼───────────────┘
                     │ (Private Subnet)
                     │
         ┌───────────┼───────────┐
         │           │           │
    ┌────▼────┐ ┌───▼────┐ ┌───▼────┐
    │PostgreSQL│ │ Redis  │ │   S3   │
    │ (Private)│ │(Private)│ │(Bucket)│
    └──────────┘ └────────┘ └────────┘
```

### VPC (Virtual Private Cloud) Configuration

**Subnets**:
- **Public Subnet**: Load balancers, NAT gateways
- **Private Subnet (App)**: API Gateway, services
- **Private Subnet (Data)**: Databases, Redis

**Security Groups**:
| Resource | Inbound Rules | Outbound Rules |
|----------|---------------|----------------|
| API Gateway | Port 443 (from Load Balancer) | All (to services) |
| Services | Port 8080 (from API Gateway) | All (to databases) |
| PostgreSQL | Port 5432 (from services only) | None |
| Redis | Port 6379 (from services only) | None |

**Network ACLs**:
- Deny all traffic by default
- Allow only required ports/protocols
- Block suspicious IP ranges (threat intelligence feeds)

### WAF (Web Application Firewall)

**Managed Rules** (AWS WAF, Cloudflare):
1. **Core Rule Set**: OWASP Top 10 protection
2. **Known Bad Inputs**: SQL injection, XSS
3. **Rate-Based Rules**: Block IPs with >2000 req/5min
4. **IP Reputation**: Block known malicious IPs
5. **Geographic Blocking**: Optional (block countries with high fraud)

**Custom Rules**:
- Block requests with SQL keywords in query params
- Block requests with suspicious user-agents
- Require `User-Agent` header (block bots)

### DDoS Protection

**Strategies**:
1. **CloudFront/CDN**: Absorb layer 3/4 attacks
2. **AWS Shield Standard**: Automatic DDoS protection
3. **Rate Limiting**: Throttle requests per IP
4. **Auto-Scaling**: Scale out to handle traffic spikes
5. **Geo-Blocking**: Optional, based on threat intel

---

## Secrets Management

### Secret Storage

**Technology**: AWS Secrets Manager or HashiCorp Vault

**Secrets to Store**:
- Database credentials
- Redis connection strings
- API keys (sports data providers)
- JWT signing keys (private key)
- S3 access credentials
- Third-party service keys (Stripe, SendGrid)

**Access Control**:
- Secrets accessible only via IAM roles (no hardcoded credentials)
- Rotate secrets every 90 days
- Audit all secret access attempts

### Secret Rotation

**Automatic Rotation**:
- Database passwords: Every 90 days
- JWT signing keys: Every 90 days
- API keys: Manual rotation (if provider supports)

**Rotation Process**:
1. Generate new secret
2. Update Secrets Manager
3. Graceful cutover (support both old + new for 1 hour)
4. Invalidate old secret
5. Verify no errors in logs

### Environment Variables

**DO NOT store secrets in environment variables** (visible in process list)

**Alternative**: Fetch from Secrets Manager at startup

---

## Compliance & Privacy

### GDPR (General Data Protection Regulation)

**User Rights**:
1. **Right to Access**: Provide user's data upon request
2. **Right to Erasure**: Delete user data (account deletion)
3. **Right to Portability**: Export user data (JSON format)
4. **Right to Rectification**: Allow users to update data

**Implementation**:
- `GET /users/me/data` - Export user data
- `DELETE /users/me` - Delete account (anonymize data)
- Consent tracking: Log when user accepts terms/privacy policy

**Data Retention**:
- User data: Retain until account deleted
- Logs: Retain 90 days max
- Backups: Retain 30 days, then purge

### CCPA (California Consumer Privacy Act)

**Requirements** (if applicable):
- Disclose data collection practices
- Allow users to opt-out of data sale (not applicable if no data sold)
- Provide data deletion upon request

### PCI-DSS (Payment Card Industry Data Security Standard)

**Scope**: If handling payment data directly

**Strategy**: **Avoid PCI scope** by using payment processor (Stripe)
- Stripe handles card data
- Senzu AI only stores payment token (not card details)
- Reduces compliance burden

### Audit Logging

**Events to Log**:
- User login/logout
- Permission changes (role updates)
- Model deployments
- Database schema changes
- Backup/restore operations
- Secret access attempts

**Log Fields**:
```json
{
  "timestamp": "2025-10-15T14:30:00Z",
  "event": "user_login",
  "user_id": "user_abc123",
  "ip_address": "203.0.113.45",
  "user_agent": "Mozilla/5.0...",
  "success": true
}
```

**Retention**: 1 year (for compliance)

**Access Control**: Audit logs readable only by admins

---

## Vulnerability Management

### Dependency Scanning

**Tools**:
- **Python**: `safety`, `pip-audit`
- **Node.js**: `npm audit`, `Snyk`
- **Docker**: `Trivy`, `Clair`

**Process**:
- Run daily in CI/CD pipeline
- Alert on critical/high vulnerabilities
- Auto-create tickets for remediation
- SLA: Fix critical vulns within 7 days, high vulns within 30 days

### Static Application Security Testing (SAST)

**Tools**:
- **Python**: `bandit`, `semgrep`
- **Node.js**: `ESLint` (with security plugins)

**Run**: On every pull request

**Checks**:
- SQL injection risks
- XSS risks
- Insecure randomness
- Hardcoded secrets
- Insecure crypto usage

### Dynamic Application Security Testing (DAST)

**Tools**: OWASP ZAP, Burp Suite

**Process**:
- Run weekly against staging environment
- Automated scans for common vulnerabilities
- Manual penetration testing: Annually (by security firm)

### Penetration Testing

**Frequency**: Annually (external security firm)

**Scope**:
- API security testing
- Authentication/authorization bypass attempts
- Network penetration testing
- Social engineering (optional)

**Deliverables**: Report with findings, remediation recommendations

---

## Security Incident Response

### Incident Classification

| Severity | Definition | Example |
|----------|------------|---------|
| **Critical** | Active breach, data exfiltration | Database dump leaked |
| **High** | Vulnerability exploited | SQL injection successful |
| **Medium** | Attempted attack blocked | Multiple failed login attempts |
| **Low** | Suspicious activity | Unusual traffic pattern |

### Response Plan

#### Phase 1: Detection & Analysis
1. Alert triggered (monitoring, WAF, logs)
2. Verify incident (not false positive)
3. Classify severity
4. Assemble response team

#### Phase 2: Containment
1. Isolate affected systems
2. Block attacker IP/accounts
3. Revoke compromised credentials
4. Enable additional logging

#### Phase 3: Eradication
1. Identify root cause
2. Remove attacker access
3. Patch vulnerabilities
4. Deploy security updates

#### Phase 4: Recovery
1. Restore services
2. Verify no backdoors remain
3. Monitor for re-infection
4. Communicate with users (if required)

#### Phase 5: Post-Incident
1. Write incident report
2. Conduct post-mortem
3. Update security controls
4. Notify authorities (if required by law)

### Communication Plan

**Internal**:
- Notify security team immediately
- Notify engineering leadership
- Notify legal/compliance (if data breach)

**External** (if data breach):
- Notify affected users within 72 hours (GDPR requirement)
- Notify regulatory authorities
- Public disclosure (if required)

---

## Security Best Practices (Development)

### Secure Coding Guidelines

1. **Input Validation**: Validate and sanitize all user inputs
2. **Output Encoding**: Encode data before rendering (prevent XSS)
3. **Parameterized Queries**: Use ORM or prepared statements (prevent SQL injection)
4. **Error Handling**: Don't expose stack traces to users
5. **Secure Defaults**: Secure configuration out-of-the-box
6. **Least Privilege**: Services run with minimal permissions

### Code Review Checklist

- [ ] Authentication/authorization correctly implemented
- [ ] Input validation on all user inputs
- [ ] Sensitive data not logged
- [ ] Secrets not hardcoded
- [ ] SQL queries parameterized
- [ ] Error messages don't leak sensitive info
- [ ] Rate limiting applied to endpoints
- [ ] HTTPS enforced

### Security Training

**For Developers**:
- Annual security training (OWASP Top 10)
- Secure coding workshops
- Phishing awareness training

---

## Future Enhancements

1. **Multi-Factor Authentication (MFA)**: TOTP, SMS, biometric
2. **OAuth 2.0 Integration**: Social login (Google, GitHub)
3. **API Key Management**: Allow users to generate API keys
4. **Bot Detection**: CAPTCHA, hCaptcha for suspicious activity
5. **Advanced Threat Detection**: ML-based anomaly detection
6. **Security Information and Event Management (SIEM)**: Centralized security monitoring

---

**Last Updated**: 2025-10-15
**Version**: 1.0
**Status**: Phase 3 - Production Readiness
**Owner**: Security Team, Backend Team
