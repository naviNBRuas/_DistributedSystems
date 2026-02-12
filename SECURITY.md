# Security Policy

## Supported Versions

Currently supported versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Security Considerations

### Design Philosophy

This repository provides **foundational building blocks** for distributed systems. Security is primarily the responsibility of the **consuming application**, but we provide secure-by-default implementations where applicable.

### Built-in Security Features

#### 1. Input Validation
- All public APIs validate inputs
- Type checking on critical parameters
- Resource limits enforced to prevent DoS
- Range checks on numerical parameters

#### 2. Error Handling
- No silent failures
- Clear error messages without leaking sensitive data
- Specific exception types for different failure modes
- Proper error propagation

#### 3. Concurrency Safety
- Thread-safe operations where applicable
- Proper locking mechanisms
- No race conditions in critical sections
- Atomic operations for consistency

#### 4. Resource Management
- Bounded queues to prevent memory exhaustion
- Timeouts on all blocking operations
- Proper resource cleanup (locks, connections)
- Automatic garbage collection of stale entries

### Security Assumptions

This repository **assumes** the following are implemented by consuming applications:

#### Network Security
- **TLS/SSL** for all inter-node communication
- **Mutual TLS (mTLS)** for node authentication
- **Message authentication** (HMAC, digital signatures)
- **Network isolation** (VPCs, firewalls)

#### Authentication & Authorization
- **Node identity verification** before allowing joins
- **Access control** for operations (read/write permissions)
- **API authentication** (tokens, certificates)
- **Rate limiting** per authenticated entity

#### Data Security
- **Encryption at rest** for persistent state
- **Encryption in transit** (TLS)
- **Secure key management** (key rotation, HSMs)
- **Audit logging** of security-relevant operations

### Known Security Limitations

#### 1. Byzantine Consensus Module
- Requires **cryptographic signatures** for message authentication
- Signatures **not implemented** in this stdlib-only version
- **Implementer must add** cryptographic library (e.g., `cryptography`)
- Use for Byzantine scenarios only with proper signatures

#### 2. Network Communication
- No built-in encryption (assumes TLS layer)
- No message authentication codes
- No replay attack prevention
- **Must be added by implementer**

#### 3. Fencing Tokens
- Monotonic token generation provided
- **Token storage security** is implementer's responsibility
- Tokens should be validated by backend systems
- No built-in token encryption

#### 4. Service Discovery
- No authentication on registration
- No authorization for discovery
- Assumes trusted network environment
- **Add authentication layer in production**

### Security Best Practices for Users

#### 1. Network Configuration

```python
# ❌ DON'T: Expose services on public interfaces
node = RaftNode(node_id="node1", bind_address="0.0.0.0")

# ✅ DO: Bind to private network interfaces
node = RaftNode(node_id="node1", bind_address="10.0.1.10")

# ✅ DO: Use TLS for communication (implement wrapper)
class SecureRaftNode(RaftNode):
    def send_message(self, peer, message):
        encrypted = tls_encrypt(message)
        super().send_message(peer, encrypted)
```

#### 2. Input Validation

```python
# ✅ DO: Validate inputs before processing
def replicate_data(key, value):
    if not isinstance(key, str):
        raise ValueError("Key must be string")
    if len(key) > MAX_KEY_LENGTH:
        raise ValueError("Key too long")
    if len(value) > MAX_VALUE_LENGTH:
        raise ValueError("Value too large")
    
    return raft.replicate_entry({key: value})
```

#### 3. Resource Limits

```python
# ✅ DO: Set resource limits
lock_manager = LockManager(
    max_locks_per_client=100,
    lock_timeout_sec=30,
    max_wait_time_sec=60
)

rate_limiter = TokenBucketLimiter(
    rate=1000,  # requests/sec
    capacity=5000,  # max burst
    per_user=True  # per-user limits
)
```

#### 4. Audit Logging

```python
# ✅ DO: Log security-relevant operations
import logging

security_logger = logging.getLogger('security')

def acquire_lock(resource, owner):
    result = lock_manager.acquire(resource, owner)
    security_logger.info(f"Lock acquisition: resource={resource}, owner={owner}, success={result}")
    return result
```

#### 5. Access Control

```python
# ✅ DO: Implement access control
def check_permission(user, operation, resource):
    if user not in authorized_users:
        raise PermissionError("User not authorized")
    
    if operation == "write" and user not in write_users:
        raise PermissionError("Write access denied")
    
    return True

def write_data(user, key, value):
    check_permission(user, "write", key)
    return service.set(key, value)
```

## Reporting a Vulnerability

### How to Report

If you discover a security vulnerability, please **DO NOT** open a public issue. Instead:

1. **Email**: founder@nbr.company (replace with your security contact)
2. **Subject**: `[SECURITY] DistributedSystems - <brief description>`
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Confirmation**: Within 5 business days
- **Fix Timeline**: Depends on severity
  - Critical: 7-14 days
  - High: 30 days
  - Medium: 60 days
  - Low: 90 days

### Disclosure Policy

- **Coordinated Disclosure**: We follow responsible disclosure
- **Embargo Period**: 90 days from report
- **Credit**: Reporter will be credited (unless anonymity requested)
- **CVE Assignment**: For critical/high severity issues

## Security Advisories

Security advisories will be published at:
- GitHub Security Advisories
- Repository CHANGELOG.md
- Release notes

## Security Checklist for Production Use

Before deploying to production:

### Network Security
- [ ] TLS/SSL configured for all inter-node communication
- [ ] mTLS enabled for node authentication
- [ ] Network isolated (VPC, firewall rules)
- [ ] DDoS protection in place

### Authentication & Authorization
- [ ] Node identity verification implemented
- [ ] API authentication configured
- [ ] Access control policies defined
- [ ] Rate limiting per user/IP

### Data Security
- [ ] Encryption at rest enabled
- [ ] Secure key management (rotation, HSMs)
- [ ] Audit logging configured
- [ ] Sensitive data sanitized in logs

### Operational Security
- [ ] Security monitoring and alerting
- [ ] Incident response plan
- [ ] Regular security audits
- [ ] Dependency scanning (for dev dependencies)
- [ ] Penetration testing completed

### Code Security
- [ ] Input validation on all APIs
- [ ] Resource limits configured
- [ ] Error handling doesn't leak info
- [ ] Security-relevant operations logged

## Additional Resources

### Security Guides
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

### Distributed Systems Security
- "Secure Distributed Computing" (various papers)
- "Byzantine Fault Tolerance" (Lamport et al.)
- "Practical Byzantine Fault Tolerance" (Castro & Liskov)

### Python Security
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security.html)
- [Bandit Security Linter](https://github.com/PyCQA/bandit)

## Contact

- **Security Email**: founder@nbr.company
- **General Questions**: See CONTRIBUTING.md
- **Bug Reports**: GitHub Issues (for non-security bugs)

---

**Last Updated**: February 6, 2026
**Version**: 0.1.0

We take security seriously and appreciate responsible disclosure.
