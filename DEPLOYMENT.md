# Deployment Guide

This guide covers deployment of the **Streamlit Web Interface**.

## Table of Contents

1. [Streamlit Web App Deployment](#streamlit-web-app-deployment)
2. [Performance Optimization](#performance-optimization)
3. [Security Considerations](#security-considerations)
4. [Monitoring](#monitoring)
5. [Scaling](#scaling)

## Streamlit Web App Deployment

### Option 1: Streamlit Cloud (Recommended - Free)

**Pros:**
- Free hosting for public apps
- Automatic deployment from GitHub
- SSL certificate included
- Easy to set up

**Cons:**
- Public by default (can use password protection)
- Resource limits on free tier
- Max 1GB storage

**Steps:**

1. **Prepare your repository:**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Sign up at [share.streamlit.io](https://share.streamlit.io)**

3. **Deploy:**
   - Click "New app"
   - Select your repository
   - Set main file: `streamlit_app.py`
   - Click "Deploy"

4. **Upload data:**
   - Option A: Commit `data/damages_with_embeddings.json` to Git
   - Option B: Use Git LFS for large files
   - Option C: Host data on S3 and modify app to fetch from S3

### Option 2: AWS (S3 + Lambda + API Gateway)

**Pros:**
- Highly scalable
- Pay only for what you use
- Can be private
- Fast global CDN

**Cons:**
- More complex setup
- Requires AWS knowledge
- Costs money (usually $5-20/month for small traffic)

**Architecture:**
```
User Browser
    ↓
CloudFront (CDN)
    ↓
S3 (Static Hosting) + API Gateway
    ↓
Lambda (Search Function)
    ↓
S3 (Data Bucket)
```

**Steps:**

1. **Upload data to S3:**
   ```bash
   aws s3 cp data/damages_with_embeddings.json s3://your-bucket/data/
   ```

2. **Create Lambda function** for search logic (convert streamlit_app.py search function)

3. **Set up API Gateway** to expose Lambda function

4. **Build static frontend** (convert Streamlit to React/Vue) or use Streamlit on EC2

### Option 3: DigitalOcean App Platform

**Pros:**
- Simple deployment
- Affordable ($5-12/month)
- Good for small-medium traffic
- Private by default

**Steps:**

1. **Push to GitHub**

2. **Create DigitalOcean account**

3. **Create new app:**
   - Connect GitHub repository
   - Select "Python" app
   - Set run command: `streamlit run streamlit_app.py --server.port=8080`
   - Deploy

4. **Environment variables:**
   - `STREAMLIT_SERVER_PORT=8080`
   - `STREAMLIT_SERVER_ADDRESS=0.0.0.0`

### Option 4: Heroku

**Pros:**
- Simple deployment
- Free tier available (with limitations)
- Easy scaling

**Cons:**
- Free tier has sleep time
- Paid plans more expensive than alternatives

**Setup:**

1. **Create `Procfile`:**
   ```
   web: streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0
   ```

2. **Create `setup.sh`:**
   ```bash
   mkdir -p ~/.streamlit/
   echo "[server]
   port = $PORT
   enableCORS = false
   headless = true
   " > ~/.streamlit/config.toml
   ```

3. **Deploy:**
   ```bash
   heroku login
   heroku create your-app-name
   git push heroku main
   ```

### Option 5: Self-Hosted VPS (DigitalOcean, Linode, Vultr)

**Pros:**
- Full control
- Predictable costs
- Can run multiple apps
- Private by default

**Cons:**
- Requires server management
- You handle security/updates
- Need to set up SSL

**Steps:**

1. **Get a VPS** ($5-10/month for basic)

2. **Set up server:**
   ```bash
   # SSH into server
   ssh root@your-server-ip

   # Update system
   apt update && apt upgrade -y

   # Install Python
   apt install python3 python3-pip python3-venv -y

   # Install nginx
   apt install nginx -y

   # Clone your repo
   git clone https://github.com/hordruma/ON_damages_compendium.git
   cd ON_damages_compendium

   # Install dependencies
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Set up systemd service:**

   Create `/etc/systemd/system/damages-compendium.service`:
   ```ini
   [Unit]
   Description=Ontario Damages Compendium
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/root/ON_damages_compendium
   Environment="PATH=/root/ON_damages_compendium/venv/bin"
   ExecStart=/root/ON_damages_compendium/venv/bin/streamlit run streamlit_app.py --server.port=8501

   [Install]
   WantedBy=multi-user.target
   ```

   Enable and start:
   ```bash
   systemctl enable damages-compendium
   systemctl start damages-compendium
   ```

4. **Configure nginx reverse proxy:**

   Create `/etc/nginx/sites-available/damages-compendium`:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8501;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

   Enable site:
   ```bash
   ln -s /etc/nginx/sites-available/damages-compendium /etc/nginx/sites-enabled/
   nginx -t
   systemctl restart nginx
   ```

5. **Set up SSL with Let's Encrypt:**
   ```bash
   apt install certbot python3-certbot-nginx -y
   certbot --nginx -d your-domain.com
   ```

## Performance Optimization

### 1. Reduce JSON file size

The embeddings file can be large. Options:

**Use compression:**
```python
import gzip
import json

# When saving:
with gzip.open('data/damages_with_embeddings.json.gz', 'wt') as f:
    json.dump(cases, f)

# When loading:
with gzip.open('data/damages_with_embeddings.json.gz', 'rt') as f:
    cases = json.load(f)
```

**Store embeddings separately:**
- Keep embeddings in a vector database (Qdrant, Pinecone, Weaviate)
- Keep case data in JSON/SQLite
- Load embeddings on-demand

### 2. Use vector database for search

For faster similarity search on large datasets:

**Qdrant (self-hosted or cloud):**
```python
from qdrant_client import QdrantClient

client = QdrantClient("localhost", port=6333)
# Store and search embeddings efficiently
```

**Pinecone (cloud):**
```python
import pinecone
pinecone.init(api_key="your-key")
index = pinecone.Index("damages-index")
# Fast vector search
```

### 3. Caching

Already implemented with `@st.cache_resource` and `@st.cache_data`

### 4. Database instead of JSON

For production with frequent updates:

**SQLite:**
```python
import sqlite3
conn = sqlite3.connect('damages.db')
# Store cases, query efficiently
```

**PostgreSQL with pgvector:**
- Native vector similarity search
- Better for concurrent users
- Scales well

## Security Considerations

### 1. Add authentication

**Streamlit-authenticator:**
```bash
pip install streamlit-authenticator
```

```python
import streamlit_authenticator as stauth

authenticator = stauth.Authenticate(...)
name, authentication_status, username = authenticator.login('Login', 'main')

if authentication_status:
    # Show app
else:
    st.error('Username/password incorrect')
```

### 2. HTTPS

Always use HTTPS in production (handled automatically by Streamlit Cloud, requires setup for self-hosted)

### 3. Rate limiting

Prevent abuse:
```python
import time
from collections import defaultdict

# Simple rate limiter
request_times = defaultdict(list)

def rate_limit(user_ip, max_requests=10, window=60):
    now = time.time()
    request_times[user_ip] = [t for t in request_times[user_ip] if now - t < window]
    if len(request_times[user_ip]) >= max_requests:
        return False
    request_times[user_ip].append(now)
    return True
```

### 4. Input validation

Already minimal risk, but always validate user input before processing

## Monitoring

### Streamlit Cloud
- Built-in analytics
- View logs in dashboard

### Self-hosted
- Set up logging:
  ```python
  import logging
  logging.basicConfig(filename='app.log', level=logging.INFO)
  ```

- Monitor with:
  - `htop` for resource usage
  - `nginx` access logs
  - Application logs

## Scaling

### If traffic grows:

1. **Vertical scaling**: Upgrade VPS/instance size
2. **Horizontal scaling**: Multiple instances + load balancer
3. **CDN**: CloudFlare in front
4. **Database**: Move to managed database
5. **Vector DB**: Use hosted Pinecone/Qdrant
6. **Serverless**: Convert to Lambda/Cloud Functions

## Cost Estimates

| Solution | Traffic Level | Estimated Monthly Cost |
|----------|---------------|------------------------|
| Streamlit Cloud | Low | $0 (free tier) |
| DigitalOcean VPS | Low-Medium | $5-12 |
| Heroku | Low | $7+ |
| AWS (optimized) | Medium | $15-30 |
| Self-hosted VPS | Any | $5-20 |

## Next Steps

1. Choose deployment method
2. Set up monitoring
3. Configure backups
4. Test thoroughly
5. Announce to users
6. Collect feedback
7. Iterate

Good luck with your deployment!
