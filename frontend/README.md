# RunCash Frontend

This is the frontend application for RunCash, a roulette tracking system.

## Features

- Real-time display of roulette numbers
- Authentication with email/password and social providers
- Strategy suggestions
- Responsive design for all devices

## Tech Stack

- React with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- Supabase for authentication
- React Router for navigation
- Shadcn UI components

## Local Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

## Deployment Options

### Vercel (Recommended)

1. Connect your repository to Vercel
2. Configure environment variables:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_KEY`
   - `VITE_API_URL`
3. Deploy with the following settings:
   - Framework: Vite
   - Build Command: `npm run build`
   - Output Directory: `dist`

### Netlify

1. Connect your repository to Netlify
2. Configure environment variables (same as above)
3. Set build command to `npm run build` and publish directory to `dist`

### Firebase Hosting

1. Install Firebase CLI: `npm install -g firebase-tools`
2. Login: `firebase login`
3. Initialize: `firebase init hosting`
4. Deploy: `firebase deploy`

## Configuration

Create a `.env` file in the frontend directory with the following variables:

```env
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_KEY=your_supabase_anon_key
VITE_API_URL=your_api_url
```

For production, ensure you set these environment variables in your hosting platform. 