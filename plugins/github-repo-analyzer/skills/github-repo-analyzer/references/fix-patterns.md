# Security Fix Patterns Catalog

Embedded reference for the `/suggest-fixes` command. Maps CWE identifiers to concrete fix pattern templates with OWASP and NIST cross-references. When generating a fix, adapt the generic pattern below to the target codebase's language, framework, and conventions.

---

## How to Use This Catalog

1. Identify the CWE(s) that match the issue's vulnerability
2. Pull the corresponding fix pattern template
3. Check "Existing Patterns in Codebase" — if the repo already solves this vulnerability elsewhere, prefer that pattern for consistency
4. Adapt the generic template to the specific language/framework
5. Cross-reference OWASP and NIST citations for the "Why This Fix Works" section

---

## CWE Top 25 — Fix Pattern Templates

### CWE-787: Out-of-bounds Write
**OWASP:** A03 Injection | **NIST:** SI-10 Information Input Validation

**Pattern:** Bounds-checking guard before write operations.
```
// PATTERN: Validate index/offset before buffer write
if (index < 0 || index >= buffer.length) {
  throw new RangeError(`Index ${index} out of bounds [0, ${buffer.length})`);
}
buffer[index] = value;
```

**Verification:** Unit test with boundary values (0, length-1, length, -1, MAX_INT).

---

### CWE-79: Cross-Site Scripting (XSS)
**OWASP:** A03 Injection | **OWASP Cheat Sheet:** Cross-Site Scripting Prevention | **NIST:** SI-10

**Pattern — Output encoding:**
```
// PATTERN: Context-aware output encoding
// HTML context: escape <, >, &, ", '
// JS context: JSON.stringify() or hex-encode
// URL context: encodeURIComponent()
// CSS context: CSS.escape() or whitelist values

// React/JSX — safe by default (no dangerouslySetInnerHTML)
<div>{userInput}</div>

// Server-side — use framework encoder
const safe = escapeHtml(userInput);
```

**Pattern — Content Security Policy:**
```
// PATTERN: CSP header to block inline scripts
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
```

**Verification:** Test with `<script>alert(1)</script>`, `javascript:alert(1)`, `" onmouseover="alert(1)`, and polyglot payloads.

---

### CWE-89: SQL Injection
**OWASP:** A03 Injection | **OWASP Cheat Sheet:** SQL Injection Prevention | **NIST:** SI-10

**Pattern — Parameterized queries:**
```
// PATTERN: Always use parameterized queries, never string concatenation
// BAD:  db.query(`SELECT * FROM users WHERE id = ${userId}`)
// GOOD: db.query('SELECT * FROM users WHERE id = $1', [userId])

// Supabase/PostgREST — use .eq() not raw SQL
const { data } = await supabase
  .from('users')
  .select('*')
  .eq('id', userId);
```

**Pattern — Stored procedures for complex queries:**
```
// PATTERN: Move complex logic to stored procedures with typed parameters
CREATE FUNCTION get_user(p_id UUID) RETURNS users AS $$
  SELECT * FROM users WHERE id = p_id;
$$ LANGUAGE sql SECURITY DEFINER;
```

**Verification:** Test with `' OR 1=1 --`, `'; DROP TABLE users; --`, union-based and time-based blind injection.

---

### CWE-416: Use After Free
**OWASP:** A04 Insecure Design | **NIST:** SI-16 Memory Protection

**Pattern:** Nullify references after deallocation; use smart pointers or managed memory.
```
// PATTERN: Set to null after free (C/C++)
free(ptr);
ptr = NULL;

// PATTERN: Use smart pointers (C++)
std::unique_ptr<Resource> resource = std::make_unique<Resource>();

// PATTERN: In managed languages, let GC handle it — avoid manual ref clearing
```

**Verification:** Memory sanitizer (ASan/MSan) under test suite.

---

### CWE-78: OS Command Injection
**OWASP:** A03 Injection | **NIST:** SI-10

**Pattern — Avoid shell execution:**
```
// PATTERN: Use language APIs instead of shell commands
// BAD:  exec(`ping ${host}`)
// GOOD: Use net module / HTTP client directly

// If shell is unavoidable, use allowlist + execFile (no shell interpretation)
const { execFile } = require('child_process');
const ALLOWED_HOSTS = ['example.com', 'api.internal'];
if (!ALLOWED_HOSTS.includes(host)) throw new Error('Host not allowed');
execFile('ping', ['-c', '1', host], callback);
```

**Verification:** Test with `; ls /`, `| cat /etc/passwd`, `` `whoami` ``, `$(id)`.

---

### CWE-20: Improper Input Validation
**OWASP:** A03 Injection, A04 Insecure Design | **OWASP Cheat Sheet:** Input Validation | **NIST:** SI-10

**Pattern — Schema validation at API boundary:**
```
// PATTERN: Validate all inputs at the API entry point using a schema library
// Zod (TypeScript)
const CreateUserSchema = z.object({
  email: z.string().email().max(254),
  name: z.string().min(1).max(100).regex(/^[a-zA-Z\s\-']+$/),
  role: z.enum(['user', 'admin', 'viewer']),
});

// Express middleware
app.post('/users', validate(CreateUserSchema), handler);
```

**Pattern — Type coercion defense:**
```
// PATTERN: Explicit type casting before use
const id = parseInt(req.params.id, 10);
if (isNaN(id) || id <= 0) return res.status(400).json({ error: 'Invalid ID' });
```

**Verification:** Fuzz with null, undefined, empty string, arrays, objects, oversized strings, unicode, special chars.

---

### CWE-125: Out-of-bounds Read
**OWASP:** A04 Insecure Design | **NIST:** SI-16

**Pattern:** Bounds check before read; use safe array access.
```
// PATTERN: Bounds-checked array access
function safeGet(arr, index) {
  if (index < 0 || index >= arr.length) return undefined;
  return arr[index];
}
```

**Verification:** Test with negative indices, length, length+1, MAX_INT.

---

### CWE-862: Missing Authorization
**OWASP:** A01 Broken Access Control | **OWASP API:** API1 BOLA, API5 BFLA | **OWASP Cheat Sheet:** Authorization | **NIST:** AC-3, AC-6

**Pattern — Route-level authorization guard:**
```
// PATTERN: Authorization middleware that verifies the requesting user
// has access to the specific resource being requested

// Express/Node
async function requireOrgMembership(req, res, next) {
  const { orgId } = req.params;
  const userId = req.user.id;

  const membership = await db.orgMembers.findFirst({
    where: { orgId, userId, status: 'active' }
  });

  if (!membership) {
    return res.status(403).json({ error: 'Not a member of this organization' });
  }

  req.orgMembership = membership;
  next();
}

// Apply to route
router.get('/orgs/:orgId/data', requireOrgMembership, getOrgData);
```

**Pattern — Row-level authorization (Supabase RLS supplement):**
```
// PATTERN: Application-level authorization check BEFORE database query
// RLS is defense-in-depth, not the sole authorization mechanism

async function getResource(userId, resourceId) {
  // Step 1: Application-level check
  const hasAccess = await checkAccess(userId, resourceId);
  if (!hasAccess) throw new ForbiddenError();

  // Step 2: Query with RLS as additional layer
  const { data } = await supabase
    .from('resources')
    .select('*')
    .eq('id', resourceId);

  return data;
}
```

**Verification:** Test with: (1) valid user accessing own resource, (2) valid user accessing another user's resource (must fail), (3) unauthenticated request, (4) admin accessing any resource, (5) deleted/suspended user.

---

### CWE-639: Authorization Bypass Through User-Controlled Key (IDOR)
**OWASP:** A01 Broken Access Control | **OWASP API:** API1 BOLA | **NIST:** AC-3

**Pattern — Ownership verification:**
```
// PATTERN: Never trust user-supplied IDs — always verify ownership
// BAD:  const data = await getInvoice(req.params.invoiceId);
// GOOD: Verify the requesting user owns the resource

async function getInvoice(req, res) {
  const invoice = await db.invoices.findFirst({
    where: {
      id: req.params.invoiceId,
      orgId: req.user.orgId  // Scoped to user's org
    }
  });

  if (!invoice) return res.status(404).json({ error: 'Not found' });
  return res.json(invoice);
}
```

**Pattern — Indirect reference map:**
```
// PATTERN: Use session-scoped indirect references instead of database IDs
// Map user-visible reference → actual database ID per session
const refMap = req.session.refMap || {};
const actualId = refMap[req.params.ref];
if (!actualId) return res.status(404).json({ error: 'Not found' });
```

**Verification:** Enumerate sequential IDs; swap IDs between authenticated sessions; test with UUIDs from other tenants.

---

### CWE-522: Insufficiently Protected Credentials
**OWASP:** A02 Cryptographic Failures, A07 Identification and Authentication Failures | **OWASP Cheat Sheet:** Credential Storage | **NIST:** IA-5, SC-28

**Pattern — Password hashing:**
```
// PATTERN: bcrypt/scrypt/argon2 with per-user salt
// BAD:  store(sha256(password))
// BAD:  store(md5(password + globalSalt))
// GOOD:
const bcrypt = require('bcrypt');
const SALT_ROUNDS = 12;
const hash = await bcrypt.hash(password, SALT_ROUNDS);
// Store hash; verify with bcrypt.compare(candidate, hash)
```

**Pattern — API key / secret storage:**
```
// PATTERN: Environment variables or secret manager — never in code or config files
// BAD:  const API_KEY = 'sk-live-abc123';
// BAD:  API_KEY=sk-live-abc123  (committed .env file)
// GOOD: process.env.API_KEY with .env in .gitignore
// BEST: Secret manager (AWS Secrets Manager, Vault, Supabase Vault)
```

**Pattern — Token rotation:**
```
// PATTERN: Short-lived tokens with refresh mechanism
// Access token: 15 min expiry
// Refresh token: 7 day expiry, single-use, rotated on each use
// Revocation: maintain a denylist or use stateless JWT with short TTL
```

**Verification:** Check that passwords are not stored in plaintext in DB; verify .env is in .gitignore; scan for hardcoded secrets with `trufflehog` or `gitleaks`.

---

### CWE-312: Cleartext Storage of Sensitive Information
**OWASP:** A02 Cryptographic Failures | **OWASP Cheat Sheet:** Cryptographic Storage | **NIST:** SC-28

**Pattern — Encrypt at rest:**
```
// PATTERN: Application-level encryption for sensitive fields
// Use AES-256-GCM with per-record keys wrapped by a master key

const crypto = require('crypto');
const algorithm = 'aes-256-gcm';

function encrypt(plaintext, key) {
  const iv = crypto.randomBytes(16);
  const cipher = crypto.createCipheriv(algorithm, key, iv);
  const encrypted = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const tag = cipher.getAuthTag();
  return { iv, encrypted, tag };  // Store all three
}
```

**Pattern — Supabase Vault for secrets:**
```
// PATTERN: Use Supabase Vault for API keys, tokens, connection strings
-- Store
SELECT vault.create_secret('stripe-key', 'sk-live-abc123', 'Stripe API key');
-- Retrieve (only in server-side functions, never exposed to client)
SELECT vault.get_secret('stripe-key');
```

**Verification:** Query the database directly for the sensitive column — it should be ciphertext, not plaintext.

---

### CWE-352: Cross-Site Request Forgery (CSRF)
**OWASP:** A01 Broken Access Control | **OWASP Cheat Sheet:** CSRF Prevention | **NIST:** SC-23

**Pattern — CSRF token (server-rendered forms):**
```
// PATTERN: Synchronizer token pattern
// Server: generate per-session token, embed in form as hidden field
// Server: validate token on every state-changing request

app.use(csrf({ cookie: true }));
app.get('/form', (req, res) => {
  res.render('form', { csrfToken: req.csrfToken() });
});
```

**Pattern — SameSite cookies + origin check (API):**
```
// PATTERN: For API-based apps, combine SameSite cookies with origin header validation
// Set-Cookie: session=abc; SameSite=Strict; Secure; HttpOnly
// Middleware: reject requests where Origin header doesn't match expected domain
```

**Verification:** Submit form from a different origin; replay request without CSRF token; test with SameSite=None.

---

### CWE-942: Permissive Cross-domain Policy (CORS)
**OWASP:** A05 Security Misconfiguration | **OWASP Cheat Sheet:** CORS | **NIST:** AC-4

**Pattern — Strict CORS allowlist:**
```
// PATTERN: Explicit origin allowlist — never reflect the Origin header or use wildcard with credentials
// BAD:  Access-Control-Allow-Origin: *
// BAD:  Access-Control-Allow-Origin: ${req.headers.origin}
// GOOD:
const ALLOWED_ORIGINS = [
  'https://app.example.com',
  'https://admin.example.com'
];

app.use(cors({
  origin: (origin, callback) => {
    if (!origin || ALLOWED_ORIGINS.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error('CORS not allowed'));
    }
  },
  credentials: true
}));
```

**Verification:** Send request with `Origin: https://evil.com` — should be rejected. Test with null origin, missing origin, and each allowed origin.

---

### CWE-306: Missing Authentication for Critical Function
**OWASP:** A07 Identification and Authentication Failures | **OWASP API:** API2 Broken Authentication | **NIST:** IA-2

**Pattern — Authentication middleware:**
```
// PATTERN: Require authentication on all routes by default; explicitly mark public routes
// Express
const requireAuth = (req, res, next) => {
  if (!req.user) return res.status(401).json({ error: 'Authentication required' });
  next();
};

// Apply globally, then exempt public routes
app.use(requireAuth);
app.get('/health', skipAuth, healthCheck);
app.get('/public/docs', skipAuth, serveDocs);
```

**Verification:** Hit every endpoint without a session/token — all should return 401 except explicitly public routes.

---

### CWE-200: Exposure of Sensitive Information to an Unauthorized Actor
**OWASP:** A01 Broken Access Control | **NIST:** AC-3, AC-4

**Pattern — Response filtering:**
```
// PATTERN: Never return full database objects — explicitly select safe fields
// BAD:  res.json(user);  // Leaks password_hash, internal_id, etc.
// GOOD:
const safeUser = {
  id: user.id,
  name: user.name,
  email: user.email,
  role: user.role
};
res.json(safeUser);
```

**Pattern — Error message sanitization:**
```
// PATTERN: Generic error messages for users; detailed errors only in server logs
// BAD:  res.status(500).json({ error: err.message, stack: err.stack });
// GOOD:
logger.error('Database error', { error: err, userId: req.user?.id });
res.status(500).json({ error: 'An internal error occurred' });
```

**Verification:** Trigger errors and inspect response bodies; check that stack traces, SQL queries, and internal paths are never exposed.

---

### CWE-532: Insertion of Sensitive Information into Log File
**OWASP:** A09 Security Logging and Monitoring Failures | **NIST:** AU-3

**Pattern — Log sanitization:**
```
// PATTERN: Redact sensitive fields before logging
function sanitizeForLog(obj) {
  const sensitive = ['password', 'token', 'secret', 'apiKey', 'ssn', 'creditCard'];
  const sanitized = { ...obj };
  for (const key of Object.keys(sanitized)) {
    if (sensitive.some(s => key.toLowerCase().includes(s))) {
      sanitized[key] = '[REDACTED]';
    }
  }
  return sanitized;
}

logger.info('User login attempt', sanitizeForLog(req.body));
```

**Verification:** Grep logs for known test credentials, tokens, PII patterns.

---

### CWE-601: URL Redirection to Untrusted Site (Open Redirect)
**OWASP:** A01 Broken Access Control | **NIST:** SI-10

**Pattern — Redirect allowlist:**
```
// PATTERN: Validate redirect targets against an allowlist
const ALLOWED_REDIRECTS = ['/dashboard', '/settings', '/billing'];

function safeRedirect(url) {
  // Only allow relative paths from the allowlist
  if (ALLOWED_REDIRECTS.includes(url)) return url;
  // Or validate it's the same origin
  try {
    const parsed = new URL(url, 'https://app.example.com');
    if (parsed.origin === 'https://app.example.com') return url;
  } catch {}
  return '/dashboard';  // Default safe redirect
}
```

**Verification:** Test with `//evil.com`, `https://evil.com`, `/\evil.com`, `javascript:alert(1)`.

---

## OWASP Application Security Verification Standard (ASVS) v4.0 — Key Requirements

Reference for the "Why This Fix Works" section. Cite the specific ASVS requirement that the fix satisfies.

### V2: Authentication
- V2.1.1: Passwords at least 12 characters
- V2.1.7: Passwords checked against breach databases
- V2.4.1: Passwords stored using bcrypt, scrypt, argon2
- V2.8.1: Time-based OTP for MFA

### V3: Session Management
- V3.2.1: Session IDs generated with at least 64 bits of entropy
- V3.3.1: Session terminated on logout
- V3.4.1: Cookie-based tokens use Secure, HttpOnly, SameSite attributes

### V4: Access Control
- V4.1.1: Application enforces access control at a trusted service layer
- V4.1.3: Principle of least privilege — deny by default
- V4.2.1: Sensitive data accessible only to authorized users

### V5: Validation, Sanitization, Encoding
- V5.1.1: Input validation at a trusted service layer
- V5.2.1: All HTML input properly sanitized
- V5.3.1: Output encoding context-appropriate

### V6: Stored Cryptography
- V6.2.1: All cryptographic operations use approved algorithms (AES, RSA, SHA-256+)
- V6.4.1: Key management through a secrets vault or KMS

### V8: Data Protection
- V8.1.1: Sensitive data classified and protected per classification level
- V8.3.1: Sensitive data not included in URL parameters

### V13: API and Web Service
- V13.1.1: All API endpoints require authentication (except explicitly public)
- V13.2.1: RESTful APIs validate content type
- V13.4.1: API responses do not expose internal implementation details

---

## OWASP Cheat Sheet Index

Quick reference for which OWASP Cheat Sheet to cite in fix reports:

| Vulnerability Domain | Cheat Sheet |
|---------------------|-------------|
| Authorization / IDOR | Authorization Cheat Sheet |
| Authentication | Authentication Cheat Sheet |
| Session management | Session Management Cheat Sheet |
| Password storage | Password Storage Cheat Sheet |
| Input validation | Input Validation Cheat Sheet |
| XSS prevention | Cross-Site Scripting Prevention Cheat Sheet |
| SQL injection | SQL Injection Prevention Cheat Sheet |
| CSRF prevention | CSRF Prevention Cheat Sheet |
| CORS configuration | CORS Cheat Sheet |
| Cryptographic storage | Cryptographic Storage Cheat Sheet |
| Error handling | Error Handling Cheat Sheet |
| Logging | Logging Cheat Sheet |
| File upload | File Upload Cheat Sheet |
| API security | REST Security Cheat Sheet |

Source: https://cheatsheetseries.owasp.org/

---

## NIST SP 800-53 Rev. 5 — Selected Controls

| Control | Name | When to Cite |
|---------|------|-------------|
| AC-2 | Account Management | User provisioning, deprovisioning, role assignment |
| AC-3 | Access Enforcement | Any authorization check — route guards, RLS, ABAC/RBAC |
| AC-4 | Information Flow Enforcement | CORS, CSP, data classification boundaries |
| AC-6 | Least Privilege | Default-deny, minimum necessary permissions |
| AU-2 | Event Logging | What events to log (auth, access control, errors) |
| AU-3 | Content of Audit Records | What fields to include in log entries |
| IA-2 | Identification and Authentication | MFA, session tokens, API keys |
| IA-5 | Authenticator Management | Password hashing, token rotation, secret storage |
| SC-8 | Transmission Confidentiality | TLS enforcement, certificate validation |
| SC-12 | Cryptographic Key Management | Key rotation, vault usage, KMS integration |
| SC-13 | Cryptographic Protection | Algorithm selection (AES-256, SHA-256+, bcrypt) |
| SC-23 | Session Authenticity | CSRF tokens, SameSite cookies |
| SC-28 | Protection of Information at Rest | Encryption at rest, Supabase Vault |
| SI-10 | Information Input Validation | Schema validation, type checking, sanitization |
| SI-11 | Error Handling | Sanitized error responses, no stack traces |

Source: https://csf.tools/reference/nist-sp-800-53/
