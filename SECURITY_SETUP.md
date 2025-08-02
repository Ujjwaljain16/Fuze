# 🔐 Security Setup Guide for Fuze

This guide explains how to properly configure HTTPS and CSRF protection for your Fuze application.

## 🚀 Quick Start

### Development Setup
```bash
# 1. Generate self-signed certificate for development
python setup_https.py dev

# 2. Update your .env file
cp env_template.txt .env
# Edit .env and set:
# HTTPS_ENABLED=True
# CSRF_ENABLED=True

# 3. Start the application
python app.py
```

### Production Setup
```bash
# 1. Get SSL certificate (Let's Encrypt recommended)
sudo certbot certonly --standalone -d yourdomain.com

# 2. Copy production environment template
cp env_production_template.txt .env

# 3. Update .env with your actual values
# SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
# SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem

# 4. Start in production mode
FLASK_ENV=production python app.py
```

## 🔧 Configuration Details

### Environment Variables

#### Development (.env)
```bash
# Security Settings
HTTPS_ENABLED=True
CSRF_ENABLED=True

# SSL Certificate Paths
SSL_CERT_PATH=certs/cert.pem
SSL_KEY_PATH=certs/key.pem

# CORS Origins
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

#### Production (.env)
```bash
# Security Settings
FLASK_ENV=production
HTTPS_ENABLED=True
CSRF_ENABLED=True

# SSL Certificate Paths
SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem

# CORS Origins (restrict to your domains)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

## 🛡️ Security Features Implemented

### 1. HTTPS Configuration
- **Automatic SSL/TLS**: Flask serves HTTPS when certificates are provided
- **Secure Cookies**: JWT cookies only sent over HTTPS in production
- **HSTS Headers**: Strict Transport Security headers in production
- **Certificate Validation**: Automatic certificate path validation

### 2. CSRF Protection
- **Token-based Protection**: CSRF tokens for all non-GET requests
- **Automatic Token Management**: Frontend automatically handles CSRF tokens
- **Error Handling**: Proper error responses for CSRF failures
- **Token Refresh**: Automatic CSRF token refresh on errors

### 3. JWT Security
- **HTTP-only Cookies**: Refresh tokens stored in secure HTTP-only cookies
- **Short-lived Access Tokens**: 15-minute expiration for access tokens
- **Automatic Refresh**: Seamless token refresh in frontend
- **Secure Headers**: Authorization headers for access tokens

### 4. CORS Configuration
- **Environment-based**: Different CORS settings for dev/prod
- **Credential Support**: Proper handling of cookies and credentials
- **Origin Restriction**: Production restricts to specific domains

### 5. Security Headers
- **X-Content-Type-Options**: Prevents MIME type sniffing
- **X-Frame-Options**: Prevents clickjacking attacks
- **X-XSS-Protection**: Enables browser XSS protection
- **HSTS**: Strict Transport Security (production only)

## 🔍 Testing Security

### Check SSL Requirements
```bash
python setup_https.py check
```

### Test HTTPS Connection
```bash
# Test with curl
curl -k https://localhost:5000/api/health

# Test with browser
# Navigate to https://localhost:5000
```

### Test CSRF Protection
```bash
# This should fail without CSRF token
curl -X POST https://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'

# This should work with CSRF token
curl -X POST https://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -H "X-CSRF-TOKEN: your-csrf-token" \
  -d '{"email":"test@example.com","password":"test"}' \
  --cookie "csrf_access_token=your-csrf-token"
```

## 🚨 Production Security Checklist

- [ ] **SSL Certificate**: Valid SSL certificate installed
- [ ] **HTTPS Enabled**: `HTTPS_ENABLED=True` in production
- [ ] **CSRF Enabled**: `CSRF_ENABLED=True` in production
- [ ] **Debug Disabled**: `FLASK_DEBUG=False` in production
- [ ] **Strong Secrets**: Long, random secret keys
- [ ] **CORS Restricted**: Only your domains in CORS_ORIGINS
- [ ] **Environment Set**: `FLASK_ENV=production`
- [ ] **Firewall**: Port 443 open, other ports closed
- [ ] **Regular Updates**: Keep certificates and dependencies updated

## 🔧 Troubleshooting

### Common Issues

#### 1. Certificate Errors
```bash
# Check certificate validity
openssl x509 -in certs/cert.pem -text -noout

# Regenerate if needed
python setup_https.py dev
```

#### 2. CSRF Token Errors
```bash
# Check if CSRF is enabled
curl https://localhost:5000/api/auth/csrf-token

# Verify token format
# Should return: {"csrf_token": "..."}
```

#### 3. CORS Errors
```bash
# Check CORS configuration
curl -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: X-Requested-With" \
  -X OPTIONS https://localhost:5000/api/auth/login
```

#### 4. Cookie Issues
```bash
# Check cookie settings
curl -I https://localhost:5000/api/auth/login

# Look for Set-Cookie headers with Secure and HttpOnly flags
```

### Debug Mode
For debugging security issues, temporarily enable debug mode:
```bash
FLASK_DEBUG=True python app.py
```

## 📚 Additional Resources

- [Flask-JWT-Extended Documentation](https://flask-jwt-extended.readthedocs.io/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [OWASP Security Guidelines](https://owasp.org/www-project-top-ten/)
- [Mozilla Security Headers](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers)

## 🆘 Support

If you encounter security issues:

1. Check the troubleshooting section above
2. Verify all environment variables are set correctly
3. Ensure certificates are valid and accessible
4. Check browser console for CORS/CSRF errors
5. Review Flask application logs for detailed error messages

Remember: Security is an ongoing process. Regularly update your certificates, dependencies, and security configurations. 