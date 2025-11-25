# Deployment Guide

This guide covers deployment of both the **Streamlit Web Interface** and the **MCP Server**.

## Table of Contents

1. [Streamlit Web App Deployment](#streamlit-web-app-deployment)
2. [MCP Server Deployment](#mcp-server-deployment)
3. [Performance Optimization](#performance-optimization)
4. [Security Considerations](#security-considerations)
5. [Monitoring](#monitoring)
6. [Scaling](#scaling)

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

## MCP Server Deployment

The MCP server allows integration with AI assistants like Claude Desktop, Cline, and other MCP-compatible clients.

### Prerequisites

1. **Python 3.9+** installed
2. **Data files** ready (`data/damages_with_embeddings.json`)
3. **MCP client** installed (Claude Desktop, Cline, etc.)
4. **Optional**: API keys for OpenAI or Anthropic

### Option 1: Claude Desktop (Recommended for Individual Use)

**Steps:**

1. **Locate Claude Desktop config file:**
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. **Add MCP server configuration:**
   ```json
   {
     "mcpServers": {
       "ontario-damages-compendium": {
         "command": "python",
         "args": [
           "/absolute/path/to/ON_damages_compendium/mcp_server.py"
         ],
         "env": {
           "OPENAI_API_KEY": "sk-...",
           "ANTHROPIC_API_KEY": "sk-ant-..."
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop**

4. **Verify connection:**
   - Look for 🔌 icon in Claude Desktop
   - Try: "Search the damages compendium for cervical spine injuries"

**Pros:**
- Easy setup (2-3 minutes)
- No server management needed
- Works locally on your machine
- Free (except for LLM API costs)

**Cons:**
- Only accessible on your computer
- Requires Claude Desktop to be running
- Not suitable for team deployment

### Option 2: VS Code with Cline Extension

**Steps:**

1. **Install Cline extension** in VS Code

2. **Configure MCP server** in VS Code settings:
   ```json
   {
     "cline.mcpServers": {
       "ontario-damages-compendium": {
         "command": "python",
         "args": ["/path/to/mcp_server.py"],
         "env": {
           "OPENAI_API_KEY": "sk-..."
         }
       }
     }
   }
   ```

3. **Restart VS Code**

**Pros:**
- Integrated with development environment
- Easy access while coding
- Same workflow as Claude Desktop

**Cons:**
- Requires VS Code
- Single-user only

### Option 3: System Service (Linux) - Multi-User Access

For always-on MCP server accessible by multiple clients.

**Steps:**

1. **Create systemd service file** `/etc/systemd/system/damages-mcp.service`:
   ```ini
   [Unit]
   Description=Ontario Damages Compendium MCP Server
   After=network.target

   [Service]
   Type=simple
   User=damages-user
   Group=damages-user
   WorkingDirectory=/opt/ON_damages_compendium
   Environment="OPENAI_API_KEY=sk-..."
   Environment="ANTHROPIC_API_KEY=sk-ant-..."
   ExecStart=/opt/ON_damages_compendium/venv/bin/python mcp_server.py
   Restart=on-failure
   RestartSec=10
   StandardOutput=append:/var/log/damages-mcp.log
   StandardError=append:/var/log/damages-mcp-error.log

   [Install]
   WantedBy=multi-user.target
   ```

2. **Create dedicated user:**
   ```bash
   sudo useradd -r -s /bin/false damages-user
   sudo mkdir -p /opt/ON_damages_compendium
   sudo chown damages-user:damages-user /opt/ON_damages_compendium
   ```

3. **Deploy application:**
   ```bash
   # As damages-user
   cd /opt/ON_damages_compendium
   git clone https://github.com/hordruma/ON_damages_compendium.git .
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Enable and start service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable damages-mcp
   sudo systemctl start damages-mcp
   sudo systemctl status damages-mcp
   ```

5. **Configure clients to connect:**
   - Clients on same machine can use local connection
   - For remote access, set up SSH tunnel or VPN

**Pros:**
- Always running
- Automatic restart on failure
- Multi-user access (with proper networking)
- Production-ready

**Cons:**
- Linux only
- Requires server management
- Need to set up networking for remote access

### Option 4: Docker Container - Portable Deployment

**Steps:**

1. **Create Dockerfile:**
   ```dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   # Install dependencies
   RUN apt-get update && apt-get install -y \
       build-essential \
       libgl1-mesa-glx \
       libglib2.0-0 \
       && rm -rf /var/lib/apt/lists/*

   # Copy application
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY . .

   # Run MCP server
   CMD ["python", "mcp_server.py"]
   ```

2. **Build image:**
   ```bash
   docker build -t damages-mcp-server .
   ```

3. **Run container:**
   ```bash
   docker run -d \
     --name damages-mcp \
     -v $(pwd)/data:/app/data \
     -e OPENAI_API_KEY="sk-..." \
     -e ANTHROPIC_API_KEY="sk-ant-..." \
     --restart unless-stopped \
     damages-mcp-server
   ```

4. **Connect clients:**
   - Configure MCP clients to use containerized server
   - May need to expose via network or use docker exec

**Pros:**
- Portable across systems
- Isolated environment
- Easy updates (rebuild container)
- Works on Linux, macOS, Windows

**Cons:**
- Requires Docker knowledge
- Slightly more complex setup

### Option 5: Cloud Deployment - AWS EC2

For enterprise/team deployment with high availability.

**Steps:**

1. **Launch EC2 instance:**
   - Type: t3.small or larger
   - OS: Ubuntu 22.04 LTS
   - Security Group: Allow SSH (22) and custom ports if needed

2. **Connect and install:**
   ```bash
   ssh ubuntu@your-ec2-ip

   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install Python
   sudo apt install python3 python3-pip python3-venv git -y

   # Clone repository
   git clone https://github.com/hordruma/ON_damages_compendium.git
   cd ON_damages_compendium

   # Set up virtual environment
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Set up systemd service** (same as Option 3)

4. **Configure security:**
   - Use AWS Secrets Manager for API keys
   - Set up CloudWatch for logging
   - Enable VPC for network isolation

5. **Access from clients:**
   - Use VPN or SSH tunneling
   - Or expose via API Gateway with authentication

**Pros:**
- Highly available
- Scalable
- Professional-grade
- CloudWatch monitoring

**Cons:**
- Monthly costs ($10-50)
- Requires AWS knowledge
- More complex setup

### MCP Server Configuration

#### Environment Variables

Set these via `.env` file, systemd service, or Docker:

```bash
# Required for LLM-based report analysis
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional
STREAMLIT_SERVER_PORT=8501  # If running both web and MCP
```

#### Security Best Practices

1. **API Key Management:**
   - Never commit API keys to version control
   - Use environment variables or secrets manager
   - Rotate keys regularly
   - Use separate keys for dev/prod

2. **Network Security:**
   - Run MCP server locally when possible
   - For remote access, use VPN or SSH tunneling
   - Don't expose directly to internet

3. **Data Security:**
   - Temporary PDF files deleted after analysis
   - No persistent storage of uploaded files
   - Audit logs for all searches

#### Monitoring MCP Server

**Check if running:**
```bash
# Systemd
sudo systemctl status damages-mcp

# Docker
docker ps | grep damages-mcp

# Process
ps aux | grep mcp_server.py
```

**View logs:**
```bash
# Systemd
sudo journalctl -u damages-mcp -f

# Docker
docker logs -f damages-mcp

# File-based
tail -f /var/log/damages-mcp.log
```

**Health check:**
```bash
# Check if process is responsive
python -c "import json; print(json.dumps({'status': 'ok'}))" | python mcp_server.py
```

#### Troubleshooting MCP Server

**Server not connecting:**
1. Check Python path in MCP config is absolute
2. Verify environment variables are set
3. Check file permissions on `mcp_server.py`
4. Restart MCP client

**Import errors:**
```bash
# Ensure all dependencies installed
pip install -r requirements.txt

# Check Python version
python --version  # Should be 3.9+
```

**Data not found:**
```bash
# Verify embeddings file exists
ls -lh data/damages_with_embeddings.json

# If missing, generate it:
jupyter notebook 01_extract_and_embed.ipynb
```

**Out of memory:**
- Increase system RAM
- Use smaller batch sizes
- Consider vector database for large datasets

### MCP Server Updates

**Update code:**
```bash
cd /path/to/ON_damages_compendium
git pull origin main
pip install -r requirements.txt --upgrade

# If systemd service
sudo systemctl restart damages-mcp

# If Docker
docker restart damages-mcp
```

**Update data:**
```bash
# Place new compendium PDF in project root
jupyter notebook 01_extract_and_embed.ipynb
# Run all cells

# Restart server to load new data
```

For complete MCP usage instructions, see [MCP_GUIDE.md](MCP_GUIDE.md).

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
