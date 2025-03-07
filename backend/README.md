# RunCash Backend

This directory contains two main components:
1. **API:** Express.js server to serve roulette data
2. **Scraper:** Python script to collect roulette data

## API

The API serves as an intermediary between the frontend and the Supabase database. It provides endpoints for accessing roulette data.

### Endpoints

- `GET /api/roletas` - Get all roulettes
- `GET /api/roletas/latest` - Get latest numbers for all roulettes
- `GET /api/roletas/:id` - Get details for a specific roulette
- `GET /api/health` - Health check endpoint

### Deployment Options

#### Railway (Recommended)

1. Create a new project in Railway
2. Add your GitHub repository
3. Configure environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `PORT`
4. Set the startup command to `cd backend/api && npm start`

#### Render

1. Create a new Web Service in Render
2. Connect your repository
3. Set the build command to `cd backend/api && npm install`
4. Set the start command to `cd backend/api && npm start`
5. Add the environment variables

#### Heroku

1. Create a new app in Heroku
2. Connect your repository
3. Add a Procfile with: `web: cd backend/api && npm start`
4. Set the environment variables in the dashboard

## Scraper

The scraper collects data from online roulettes and stores it in Supabase.

### Running 24/7

#### Option 1: Virtual Private Server (VPS)

1. Get a VPS (DigitalOcean, Linode, AWS EC2, etc.)
2. Install Python and dependencies:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip
   cd backend/scraper
   pip install -r requirements.txt
   ```
3. Install PM2 to keep the script running:
   ```bash
   npm install -g pm2
   pm2 start app.py --interpreter=python3
   pm2 save
   pm2 startup
   ```

#### Option 2: Railway

1. Create a new project in Railway
2. Add the GitHub repository
3. Set up environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `SCRAPE_INTERVAL_MINUTES`
   - `ALLOWED_ROULETTES`
4. Set the startup command to `cd backend/scraper && pip install -r requirements.txt && python app.py`

#### Option 3: GitHub Actions

You can use GitHub Actions to run the scraper on a schedule (note: not truly 24/7, but could run every 5-10 minutes):

```yaml
name: Run Scraper

on:
  schedule:
    - cron: '*/5 * * * *'  # Run every 5 minutes

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          cd backend/scraper
          pip install -r requirements.txt
      - name: Run scraper
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          ALLOWED_ROULETTES: ${{ secrets.ALLOWED_ROULETTES }}
        run: |
          cd backend/scraper
          python app.py
```

## Configuration

Both components use environment variables for configuration. Make sure to set them in your deployment platform.

### API Environment Variables
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
PORT=3001
```

### Scraper Environment Variables
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SCRAPE_INTERVAL_MINUTES=5
ALLOWED_ROULETTES=2010016,2380335,2010065,2010096,2010017,2010098
``` 