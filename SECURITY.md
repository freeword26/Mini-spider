# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 3.0.x   | Yes       |
| < 3.0   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in spider_max, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Email the maintainers directly with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if available)

## Security Considerations

### Authentication & Authorization
- spider_max uses RBAC (Role-Based Access Control)
- Super admin role bypasses all permission checks
- All operations are logged in `audit_log`

### Data Protection
- Database connections use WAL mode for integrity
- Backup files include SHA256 checksums
- Environment variables for sensitive configuration

### Network Security
- CORS middleware enabled by default (configure for production)
- Health check endpoints are unauthenticated
- API endpoints should be behind reverse proxy in production

### Dependencies
- All dependencies are pinned in `pyproject.toml`
- Use `pip audit` to check for known vulnerabilities
