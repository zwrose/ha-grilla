# Security Policy

## Reporting a Vulnerability

If you discover a security issue in ha-grilla — including anything related to
credential handling, token storage, or authentication flows — please report it
**privately** through GitHub's private vulnerability reporting: open the
repository's **Security** tab and choose **Report a vulnerability**
(<https://github.com/zwrose/ha-grilla/security/advisories/new>). Do NOT open a
public GitHub issue for security vulnerabilities.

## Sensitive Data Warning

This integration stores a Grilla account **refresh token** in Home Assistant's
configuration storage. The refresh token grants ongoing access to your Grilla
account and should be treated as a secret.

The refresh token can be revoked at any time by changing your Grilla account
password. After a password change, the integration will prompt you to
re-authenticate.

**Never paste logs, debug output, or diagnostic information that may contain
tokens or credentials into public GitHub issues, pull requests, or forums.**
The diagnostics download (Settings → Devices & Services → Grilla Grills → ⋮ →
Download diagnostics) automatically redacts credentials and tokens, but always
verify before sharing.

Enabling **debug logging** for the AWS/auth loggers this integration relays
(`aiogrilla`, `pycognito`, `boto3`, `awscrt`) can surface authentication-flow
detail in `home-assistant.log`. Sanitize such logs before sharing them.

If you need to share a diagnostic trace to report a non-security bug, review it
for sensitive values before posting. The maintainer may ask for a sanitized log
over private email if needed to diagnose an issue.

## Scope

Security issues in scope for private disclosure include:

- Credential or token leakage (e.g., logged to stdout/stderr in a way users
  would not expect)
- Insecure TLS/transport handling
- Issues that could allow an attacker to gain access to another user's grill or
  account credentials

Issues outside scope (treat as normal bugs):

- Breakage caused by the vendor changing their cloud service
- Feature requests
