# Render Deployment Guide

Complete step-by-step instructions for deploying the Candidate Ranking System to Render.

## Why Render?

- **Free tier available** for testing (perfect for quick deployment)
- **GitHub integration** - automatic deployments on push
- **PostgreSQL support** - better than SQLite for production
- **Environment variables** - secure secret management
- **Minimal configuration** - requires only Procfile and .env setup

---

## Prerequisites

1. **Render Account** - Sign up at [render.com](https://render.com)
2. **GitHub Repository** - Code pushed to GitHub (public or private)
3. **Environment Variables Ready**:
   - `FLASK_ENV=production`
   - `SECRET_KEY` (generate one)
   - `GOOGLE_API_KEY` (your API key)

---

## Step 1: Generate SECRET_KEY

```bash
# Run this locally to generate a secure key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output — you'll need it in Step 5.

---

## Step 2: Connect GitHub Repository

1. Go to [render.com](https://render.com) and login
2. Click **New +** button → **Web Service**
3. Select **Connect a repository**
4. Authorize GitHub and select your repository:
   - `indiranivas/levelshift_mini_project`
5. Click **Connect**

---

## Step 3: Configure Web Service

### Basic Settings

| Setting | Value |
|---------|-------|
| **Name** | `hiring-system` (or your preferred name) |
| **Runtime** | `Python 3.11` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn wsgi:app` |
| **Instance Type** | `Free` (for testing) or `Standard` (production) |

### Build Logs

Make sure build command is:
```
pip install -r requirements.txt
```

Start command is:
```
gunicorn wsgi:app
```

---

## Step 4: Connect PostgreSQL Database (Recommended)

SQLite won't work reliably on Render because the filesystem is ephemeral (gets deleted on restart).

### Option A: Use Render PostgreSQL (Recommended)

1. In Render dashboard, click **New +** → **PostgreSQL**
2. Configure:
   - **Name**: `hiring-db`
   - **Database**: `hiring`
   - **User**: `postgres`
   - **Region**: Same as web service
   - **Instance Type**: `Free` (for testing)

3. After creation, you'll get a **Internal Database URL**

4. Copy the connection string (looks like):
   ```
   postgresql://user:password@host:5432/hiring
   ```

### Option B: Stick with SQLite (Faster to Deploy)

If using SQLite:
- Data will be lost on service restart (Render redeploys frequently)
- Only suitable for development/testing
- Recommended: Upgrade to PostgreSQL when ready for production

---

## Step 5: Set Environment Variables

### In Render Dashboard

1. Go to your **Web Service** settings
2. Scroll to **Environment Variables**
3. Add each variable:

```
FLASK_ENV              production

SECRET_KEY             <paste-from-step-1>

GOOGLE_API_KEY         AIza...  (your actual API key)

DATABASE_URL           postgresql://user:password@host:5432/hiring
                       (if using PostgreSQL from Step 4)

DATABASE_PATH          hiring.db
                       (if using SQLite - not persisted)

UPLOAD_FOLDER          /var/tmp/uploads

LOG_LEVEL              INFO

PREFERRED_URL_SCHEME   https

SESSION_COOKIE_SECURE  true
```

### Critical: NEVER add these to code or .env file

Environment variables entered in Render dashboard are encrypted and secure.

---

## Step 6: Update Configuration for PostgreSQL (Optional)

If using PostgreSQL from Step 4, update `config.py`:

```python
# In config.py, add PostgreSQL support
import os

class ProductionConfig:
    # ... existing config ...
    
    # Use DATABASE_URL if available (Render PostgreSQL)
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Fallback to SQLite
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.getenv('DATABASE_PATH', 'hiring.db')}"
```

**Note**: The current app uses SQLite directly, not SQLAlchemy. For production on Render, consider migrating to SQLAlchemy with PostgreSQL support.

---

## Step 7: Deploy

### Automatic Deployment (Recommended)

1. In Render dashboard, click **Create Web Service**
2. Render will:
   - Pull code from GitHub
   - Install dependencies from `requirements.txt`
   - Run build command
   - Start app with `gunicorn wsgi:app`
3. View deployment logs in **Events** tab

### Manual Deployment

Push to GitHub (if auto-deploy enabled):
```bash
git push origin testing
```

Render will automatically detect the push and redeploy.

### Deployment URL

After successful deployment, Render assigns a URL like:
```
https://hiring-system.onrender.com
```

This is your production URL. Share this with users.

---

## Step 8: Verify Deployment

### Check Logs

In Render dashboard:
1. Click your web service
2. Go to **Logs** tab
3. Look for:
   ```
   Flask app initialized with config: production
   Ensemble model loaded successfully
   TF-IDF vectorizer loaded successfully
   ```

### Test Application

```bash
# Test health endpoint
curl https://hiring-system.onrender.com/health

# Should return:
# {"status": "healthy"}
```

### Test GenAI Integration

1. Navigate to `https://hiring-system.onrender.com/chatbot`
2. Ask a question about candidates
3. Should get GenAI response (if API key is valid)

---

## Troubleshooting

### 1. Application Won't Start

**Error in logs**: `ModuleNotFoundError`

```bash
# Solution: Check requirements.txt has all dependencies
pip install -r requirements.txt

# Push updated requirements.txt
git add requirements.txt
git commit -m "Update dependencies"
git push origin testing
```

### 2. GenAI Not Working

**Error**: "GOOGLE_API_KEY environment variable not set"

```
Solution:
1. Check Render dashboard → Environment Variables
2. Verify GOOGLE_API_KEY is set
3. Check it's not quoted: "APIkey123" ❌ vs APIkey123 ✅
4. Redeploy: Click Manage > Redeploy
```

### 3. Database Connection Failed

**Error**: "psycopg2.OperationalError"

```
Solution (PostgreSQL):
1. Verify DATABASE_URL is correct in environment variables
2. Check PostgreSQL instance is running
3. Ensure web service and database are in same region
4. Try restarting PostgreSQL instance
```

### 4. Static Files Not Loading

**Issue**: CSS/JS not loading (404 errors)

```
Solution:
1. Ensure static files are in app/static/
2. Gunicorn by default doesn't serve static files
3. In production, use Render's static site for CSS/JS
   Or configure Nginx in front of gunicorn
```

### 5. Uploads Directory Issues

**Error**: "No such file or directory: uploads"

```
Solution:
1. Create uploads directory in code:
   os.makedirs(UPLOAD_FOLDER, exist_ok=True)
2. Or use /tmp for ephemeral storage
3. For persistent files, use AWS S3 or similar
```

---

## Database Persistence

### SQLite (Current - Not Recommended)

**Pros**:
- Fast to set up
- No additional services

**Cons**:
- Data lost on Render restarts
- Limited to ~50MB file size
- No concurrent access

**Keep SQLite if**: Testing/development only

### PostgreSQL (Recommended for Production)

**Pros**:
- Data persists across restarts
- Unlimited storage
- Concurrent access support
- Automatic backups

**Setup**:

1. Create PostgreSQL database in Render
2. Get connection string from Render dashboard
3. Set `DATABASE_URL` environment variable
4. Install: `pip install psycopg2-binary SQLAlchemy`
5. Migrate app to use SQLAlchemy ORM

**Migration Example**:

```python
# Update your database queries to use SQLAlchemy
from flask_sqlalchemy import SQLAlchemy

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
db = SQLAlchemy(app)

# Define models and use ORM instead of raw SQL
```

---

## Performance Optimization

### 1. Gunicorn Workers Configuration

Update `Procfile`:
```
web: gunicorn -w 4 -b 0.0.0.0:$PORT wsgi:app
```

Workers = `2 × CPU cores + 1` (typically 4-8)

For Render Free tier, stick with default (1 worker).

### 2. Enable Caching

Use Redis for session storage and caching:

```bash
# In Render, create Redis instance
# Add REDIS_URL to environment variables
```

### 3. Database Optimization

- Add indexes on frequently queried columns
- Use connection pooling
- Archive old data periodically

---

## Security Checklist

- ✅ **Secrets not in code** - All in Render environment variables
- ✅ **HTTPS enabled** - Automatic with Render
- ✅ **Debug disabled** - `FLASK_ENV=production`
- ✅ **API key not exposed** - Uses environment variable
- ✅ **Database URL not in code** - Uses environment variable
- ✅ **SESSION_COOKIE_SECURE=true** - HTTPS only
- ✅ **X-Frame-Options headers** - Adds security headers

---

## Monitoring & Maintenance

### View Logs

```bash
# In Render dashboard
Logs tab → Stream logs in real-time
```

### Common Logs to Monitor

```
- "GenAI call successful" → API working
- "No matching candidates" → RAG working
- "ERROR" → Issues to investigate
- "WARNING" → Non-critical but watch
```

### Restart Application

Sometimes needed if state gets corrupted:

```
Dashboard → Manage → Restart Instance
```

### View Metrics

In Render dashboard → **Metrics** tab:
- CPU usage
- Memory usage
- Request count
- Error rate

---

## Upgrade to Paid Plan

When ready for production:

1. **Paid Web Service** - $7/month & up
   - More reliable (not spun down)
   - Better performance
   - More memory

2. **Paid PostgreSQL** - $15/month & up
   - Larger database
   - Automatic backups
   - Point-in-time recovery

---

## Next Steps

1. ✅ Create Render account
2. ✅ Connect GitHub repository
3. ✅ Configure web service (gunicorn)
4. ✅ Add environment variables
5. ✅ Deploy (Render handles everything)
6. ✅ Test application endpoints
7. ✅ Monitor logs for issues
8. ✅ Set up PostgreSQL when ready
9. ✅ Enable monitoring & backups

---

## Reference

- **Render Docs**: https://render.com/docs
- **Python on Render**: https://render.com/docs/deploy-python
- **PostgreSQL on Render**: https://render.com/docs/databases
- **Environment Variables**: https://render.com/docs/environment-variables

---

## Quick Links

| Task | Link |
|------|------|
| Dashboard | https://dashboard.render.com |
| Create Web Service | https://dashboard.render.com/create |
| Support | support@render.com |
| Status | https://status.render.com |

---

**Questions?** Check Render docs or contact support@render.com

---

## Current Application Status for Render

✅ **wsgi.py** - Entry point ready
✅ **Procfile** - Configured with gunicorn
✅ **requirements.txt** - All dependencies listed
✅ **Environment variables** - Support via os.getenv()
✅ **Production config** - Enabled
✅ **Logging** - Configured
✅ **Security headers** - Implemented

**Your app is ready to deploy to Render!**
