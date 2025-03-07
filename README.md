# RunCash - Roulette Analytics Platform

RunCash is a comprehensive platform for analyzing online roulette data, providing real-time statistics, and helping users make informed decisions.

## Project Structure

This project is organized as a monorepo with the following structure:

```
runcash/
├── frontend/         # React application with Vite
│   ├── src/          # Frontend source code
│   ├── public/       # Static assets
│   └── README.md     # Frontend-specific documentation
│
├── backend/
│   ├── api/          # Express.js API server
│   │   └── README.md # API documentation
│   └── scraper/      # Python scraper for roulette data
│       └── README.md # Scraper documentation
│
└── README.md         # This file
```

## Getting Started

### Prerequisites

- Node.js 18+ for the frontend and API
- Python 3.9+ for the scraper
- Supabase account for the database

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/runcash.git
cd runcash
```

2. Install dependencies for all projects:
```bash
# Install root dependencies
npm install

# Install frontend dependencies
cd frontend
npm install
cd ..

# Install API dependencies
cd backend/api
npm install
cd ../..

# Install scraper dependencies
cd backend/scraper
pip install -r requirements.txt
cd ../..
```

3. Set up environment variables:
   - Create `.env` files in the frontend, backend/api, and backend/scraper directories
   - See the README.md in each directory for required environment variables

## Development

### Running the Frontend

```bash
cd frontend
npm run dev
```

### Running the API

```bash
cd backend/api
npm run dev
```

### Running the Scraper

```bash
cd backend/scraper
python app.py
```

## Deployment

See the README.md files in each subdirectory for detailed deployment instructions:

- [Frontend Deployment](./frontend/README.md)
- [API Deployment](./backend/README.md)
- [Scraper Deployment](./backend/README.md)

## Features

- Real-time roulette data visualization
- Historical data analysis
- Strategy testing and simulation
- Mobile-responsive design
- User authentication (coming soon)
- Personalized alerts (coming soon)

## Tech Stack

- **Frontend**: React, TypeScript, Tailwind CSS, Shadcn UI
- **Backend API**: Node.js, Express
- **Scraper**: Python, BeautifulSoup
- **Database**: Supabase (PostgreSQL)
- **Deployment**: Vercel, Railway, GitHub Actions

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Thanks to all contributors who have helped build this project
- Special thanks to the open-source community for the tools and libraries used
