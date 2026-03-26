# Deployment Guide

This guide covers deploying the Candidate Ranking System to various hosting platforms.

## Pre-Deployment Checklist

- [ ] All environment variables configured (see `.env.example`)
- [ ] `GOOGLE_API_KEY` is set and valid
- [ ] `SECRET_KEY` is set to a cryptographically secure value
- [ ] `FLASK_ENV=production` is configured
- [ ] Database file path is persistent (not ephemeral storage)
- [ ] File uploads folder exists and is writable
- [ ] All requirements installed: `pip install -r requirements.txt`
- [ ] No `.env` file committed to git (check `.gitignore`)

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `FLASK_ENV` | Deployment environment | `production` |
| `SECRET_KEY` | Flask session encryption key | (generate with `secrets.token_urlsafe(32)`) |
| `GOOGLE_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `DATABASE_PATH` | SQLite database file path | `hiring.db` or `/var/lib/app/hiring.db` |
| `UPLOAD_FOLDER` | Resume upload directory | `uploads` or `/var/lib/app/uploads` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_DEBUG` | Debug mode (never `true` in production) | `false` |
| `PORT` | Server port | `5000` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `SESSION_COOKIE_SECURE` | HTTPS-only cookies | `true` (auto in production) |
| `PREFERRED_URL_SCHEME` | URL scheme | `https` (auto in production) |

### Generating a Secure SECRET_KEY

```python
import secrets
print(secrets.token_urlsafe(32))
```

## Deployment Platforms

### 1. Heroku (Recommended for Quick Deploy)

#### Quick Start

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login to Heroku
heroku login

# Create new app
heroku create your-app-name

# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set GOOGLE_API_KEY=YOUR_KEY_HERE
heroku config:set SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

# Add PostgreSQL addon (for persistent database)
heroku addons:create heroku-postgresql:hobby-dev

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

#### Database Migration (Heroku)

For SQLite migration to PostgreSQL (production-recommended):

```bash
# Install psycopg2
pip install psycopg2-binary

# Update config.py to use DATABASE_URL when available
# Already configured in current setup
```

#### Storage for Uploads (Heroku)

Heroku's filesystem is ephemeral. Use AWS S3 or similar:

```bash
# Install S3 library
pip install boto3

# Set S3 credentials
heroku config:set AWS_ACCESS_KEY_ID=...
heroku config:set AWS_SECRET_ACCESS_KEY=...
heroku config:set AWS_S3_BUCKET=...
```

---

### 2. AWS Elastic Beanstalk

#### Prerequisites

```bash
# Install EB CLI
pip install awsebcli

# Initialize EB
eb init -p python-3.11 hiring-system
```

#### Configuration

Create `.ebextensions/production.config`:

```yaml
option_settings:
  aws:elasticbeanstalk:application:environment:
    FLASK_ENV: production
    PYTHONPATH: /var/app/current:$PYTHONPATH
  aws:elasticbeanstalk:container:python:
    WSGIPath: wsgi:app
```

#### Deploy

```bash
# Set environment variables
eb setenv GOOGLE_API_KEY=YOUR_KEY FLASK_ENV=production SECRET_KEY=...

# Deploy
eb create hiring-system
eb deploy
```

#### RDS Database (Recommended)

```bash
# Create PostgreSQL database via AWS Console, then:
eb setenv DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/dbname
```

---

### 3. Google Cloud Platform (App Engine)

#### Setup

```bash
# Install Google Cloud SDK
# https://cloud.google.com/sdk/docs/install

gcloud init
gcloud auth application-default login
```

#### Create `app.yaml`

```yaml
runtime: python311
entrypoint: gunicorn -b :$PORT wsgi:app

env_variables:
  FLASK_ENV: "production"

env_variables_beta:
  # Store sensitive vars using Secret Manager
  GOOGLE_API_KEY: "secret:google_api_key"
  SECRET_KEY: "secret:secret_key"
```

#### Deploy

```bash
gcloud app deploy
```

#### Store Secrets

```bash
echo -n "YOUR_KEY" | gcloud secrets create google_api_key --data-file=-
gcloud secrets add-iam-policy-binding google_api_key \
  --member=serviceAccount:project-id@appspot.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

---

### 4. AWS EC2 (Full Control)

#### Setup Instance

```bash
# Launch Ubuntu 20.04 LTS instance
# SSH into instance

sudo apt update
sudo apt install -y python3-pip python3-venv nginx

# Clone repository
git clone <your-repo-url>
cd mini_project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn
```

#### Create `.env` File

```bash
cp .env.example .env
# Edit .env with your production values
nano .env
```

#### Configure Gunicorn

Create `gunicorn_config.py`:

```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
max_requests = 1000
timeout = 30
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
```

#### Configure Nginx

Create `/etc/nginx/sites-available/hiring`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/app/static/;
    }
}
```

Enable and restart:

```bash
sudo ln -s /etc/nginx/sites-available/hiring /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

#### Create Systemd Service

Create `/etc/systemd/system/hiring.service`:

```ini
[Unit]
Description=Hiring System Flask App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/mini_project
Environment="PATH=/home/ubuntu/mini_project/venv/bin"
EnvironmentFile=/home/ubuntu/mini_project/.env
ExecStart=/home/ubuntu/mini_project/venv/bin/gunicorn wsgi:app -c gunicorn_config.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Start service:

```bash
sudo systemctl start hiring
sudo systemctl enable hiring
```

#### SSL/TLS (Certbot)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d your-domain.com

# Update nginx config with SSL paths
sudo systemctl restart nginx
```

---

### 5. Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:app"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      FLASK_ENV: production
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
      SECRET_KEY: ${SECRET_KEY}
      DATABASE_PATH: /app/data/hiring.db
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
    restart: always
```

Deploy:

```bash
docker build -t hiring-system .
docker run -p 5000:5000 --env-file .env hiring-system
```

---

### 6. DigitalOcean App Platform

#### Connect Repository

1. Create new app at https://cloud.digitalocean.com/apps
2. Connect GitHub repository
3. Set environment variables in dashboard:
   ```
   FLASK_ENV=production
   GOOGLE_API_KEY=...
   SECRET_KEY=...
   ```
4. Deploy automatically

---

## Monitoring & Maintenance

### Application Logs

```bash
# Heroku
heroku logs --tail

# EC2/Systemd
sudo journalctl -u hiring -f

# Docker
docker logs -f container-id
```

### Health Check Endpoint

Add to `app/app.py`:

```python
@app.route('/health')
def health_check():
    return {'status': 'healthy'}, 200
```

Configure platform health checks to hit `/health` periodically.

### Database Backups

**SQLite backup** (EC2):

```bash
# Automated daily backup
0 2 * * * cp /path/to/hiring.db /backups/hiring-$(date +\%Y\%m\%d).db
```

**PostgreSQL backup** (Heroku/AWS):

```bash
# Heroku PostgreSQL
heroku pg:backups:schedule --at "02:00 Europe/London"

# AWS RDS
aws rds create-db-snapshot \
  --db-instance-identifier hiring-db \
  --db-snapshot-identifier hiring-backup-$(date +%Y%m%d)
```

### Performance Monitoring

- Enable application insights on your platform
- Monitor:
  - Request latency (target: <200ms)
  - Error rates (target: <1%)
  - API quota usage for Google Gemini
  - Database query performance
  - Disk usage for uploads/database

---

## Security Best Practices

### Production Checklist

- [ ] Enable HTTPS (never HTTP in production)
- [ ] Set `FLASK_ENV=production`
- [ ] Use strong, randomly generated `SECRET_KEY`
- [ ] Never commit `.env` file
- [ ] Enable database encryption (AWS RDS, etc.)
- [ ] Use specific API key with minimal permissions
- [ ] Configure CORS properly for your domain
- [ ] Enable rate limiting for `/api/ai/chat` endpoint
- [ ] Monitor logs for unusual activity
- [ ] Regularly update dependencies: `pip list --outdated`
- [ ] Use firewall rules to restrict database access

### API Key Security

- Use environment variables (✓ implemented)
- Rotate keys periodically (quarterly minimum)
- Use separate API keys for different environments
- Monitor API quota usage
- Consider API key restrictions (IP whitelist, domain restrictions)

---

## Troubleshooting

### Common Issues

**"ModuleNotFoundError"**
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# Check Python path
export PYTHONPATH=$PYTHONPATH:/path/to/app
```

**"Database locked"**
- Use PostgreSQL instead of SQLite for production
- SQLite doesn't handle concurrent writes well

**"File uploads not working"**
- Ensure `UPLOAD_FOLDER` directory exists and is writable
- Check disk space
- Verify file permissions

**"GenAI calls failing"**
- Verify `GOOGLE_API_KEY` is valid
- Check API quota and rate limits
- Review API logs at console.cloud.google.com

**"Secret key not set"**
```bash
# Generate and set
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

# Heroku
heroku config:set SECRET_KEY=$SECRET_KEY

# EC2
echo "SECRET_KEY=$SECRET_KEY" >> .env
```

---

## Performance Tips

1. **Use gunicorn workers**: `gunicorn -w 4 wsgi:app` (workers = 2 × CPU_cores + 1)
2. **Enable caching**: Consider redis for session/cache storage
3. **Database indexing**: Add indexes on frequently queried columns
4. **CDN for static files**: Use CloudFront, Cloudflare, etc.
5. **Async tasks**: Use Celery for long-running operations (GenAI calls)
6. **Connection pooling**: Use SQLAlchemy for better database connection management

---

## Support

- Flask: https://flask.palletsprojects.com/
- Werkzeug: https://werkzeug.palletsprojects.com/
- Gunicorn: https://gunicorn.org/
- Google Gemini API: https://ai.google.dev/

For issues specific to this application, check:
- `README.md` - Project overview
- `ARCHITECTURE.md` - System design
- Application logs - Detailed error messages
