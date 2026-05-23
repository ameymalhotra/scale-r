# SCALE-R Resilience Dashboard

**A comprehensive interactive mapping platform for visualizing climate resilience projects, infrastructure investments, and community risk assessments across Miami-Dade County.**

[![React](https://img.shields.io/badge/React-19.1.1-61DAFB?logo=react)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-7.1.7-646CFF?logo=vite)](https://vitejs.dev/)
[![Mapbox](https://img.shields.io/badge/Mapbox-GL%20JS-000000?logo=mapbox)](https://docs.mapbox.com/)

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technologies](#technologies)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Development](#development)
- [Project Structure](#project-structure)
- [Features in Detail](#features-in-detail)
- [Testing](#testing)
- [Data Sources](#data-sources)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Overview

The SCALE-R Resilience Dashboard is a fast, map-centric web application designed to help researchers, policymakers, and community members explore climate resilience and infrastructure projects across Miami-Dade County. The platform provides interactive visualization of adaptation strategies, project investments, and community risk assessments through an intuitive interface built on modern web technologies.

### Key Capabilities

- **Interactive Mapping**: Explore projects geographically with zoom, pan, and click interactions
- **Advanced Search**: Find projects by name, city, type, description, or category with real-time keyword highlighting
- **Multi-Layer Filtering**: Filter projects by infrastructure type, category, disaster focus, and city
- **Risk Visualization**: Overlay FEMA National Risk Index and Community Resilience Index data on census tracts
- **Project Details**: Access comprehensive project information through interactive popups
- **District Navigation**: Quickly navigate to specific cities or districts within Miami-Dade County

## Features

### Core Functionality

- **Interactive Map Visualization**
  - Mapbox GL JS-powered interactive map with smooth panning and zooming
  - Color-coded markers representing different infrastructure types
  - Satellite and standard map view toggles
  - Responsive design optimized for desktop and tablet devices

- **Intelligent Search System**
  - Real-time search across project names, cities, infrastructure types, descriptions, categories, and disaster focus areas
  - Keyword highlighting in search results for quick match identification
  - Keyboard navigation support (arrow keys, Enter, Escape)
  - Search results dropdown with project previews

- **Advanced Filtering**
  - Filter by infrastructure type (Green, Blue, Gray, Hybrid)
  - Filter by project category
  - Filter by disaster focus (Flooding, Sea Level Rise, Multi-hazard, etc.)
  - Filter by city/district
  - Multiple filter combinations supported
  - Dynamic marker visibility based on active filters

- **Census Tract Risk Visualization**
  - FEMA National Risk Index overlay
  - Community Resilience Index visualization
  - Interactive census tract popups with risk ratings
  - Toggleable risk layers with smooth transitions

- **Project Information Display**
  - Detailed project popups with comprehensive information
  - Project status indicators (Completed, Ongoing, Planned)
  - Cost information with formatted display
  - Project descriptions and metadata
  - Direct navigation from search results to project locations

- **User Experience Enhancements**
  - Smooth map transitions and animations
  - Responsive sidebar with collapsible sections
  - Visual feedback for interactions
  - Accessible keyboard navigation
  - Optimized performance for large datasets

## Technologies

### Core Stack

- **React 19.1.1** - Modern UI library for building interactive user interfaces
- **Vite 7.1.7** - Next-generation frontend build tool with fast HMR
- **Mapbox GL JS 3.15.0** - High-performance vector maps and geospatial visualization
- **Recharts 3.5.1** - Composable charting library for data visualization

### Development Tools

- **Vitest 1.0.4** - Fast unit test framework
- **React Testing Library** - Simple and complete testing utilities
- **ESLint** - Code linting and quality assurance
- **jsdom** - DOM implementation for Node.js testing

### Data Format

- **GeoJSON** - Standard format for encoding geographic data structures

## Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** 18.0.0 or higher
- **npm** 9.0.0 or higher (or yarn/pnpm equivalent)
- **Mapbox Access Token** - Required for map rendering ([Get one here](https://account.mapbox.com/access-tokens/))

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/IsAAcEdj/Climate-Resilience---Miami-Dade.git
cd Climate-Resilience---Miami-Dade
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Configure Mapbox Token

Open `src/App.jsx` and locate the Mapbox access token configuration:

```javascript
mapboxgl.accessToken = 'YOUR_MAPBOX_ACCESS_TOKEN';
```

Replace `YOUR_MAPBOX_ACCESS_TOKEN` with your actual Mapbox access token.

**Note**: For production deployments, consider using environment variables to securely manage your access token.

### 4. Verify Installation

```bash
npm run dev
```

The development server should start, and you'll see output indicating the local URL (typically `http://localhost:5173`).

## Development

### Running the Development Server

```bash
npm run dev
```

This command:
- Starts the Vite development server
- Enables Hot Module Replacement (HMR) for instant updates
- Opens the application in your default browser (or displays the URL)

The server will automatically reload when you make changes to the code.

### Building for Production

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory with:
- Minified JavaScript and CSS
- Optimized asset bundling
- Tree-shaking for smaller bundle sizes

### Previewing Production Build

```bash
npm run preview
```

Preview the production build locally before deploying to ensure everything works correctly.

### Development Workflow

1. Make changes to source files in `src/`
2. The development server automatically reloads on save
3. Test your changes in the browser
4. Run tests to ensure functionality: `npm test`
5. Build for production when ready: `npm run build`

## Project Structure

```
Climate-Resilience---Miami-Dade/
├── data/                            # CSV/Excel data for scripts (input & output)
│   ├── input/                       # Source files (LMS CSV, Our dataset CSV)
│   └── output/
│       ├── logs/
│       │   ├── geocoding/           # Geocoding log, geocoded LMS CSV, duplicate addresses
│       │   └── matched/             # Matched-project reference and pairs Excel files
│       └── merged/                  # Final merged Excel (used by seed-merged)
├── scripts/
│   ├── python/                      # Python scripts (geocoding, merge)
│   │   ├── geocode_lms.py
│   │   ├── merge_geocoding_log.py
│   │   ├── merge_lms_to_our_dataset.py
│   │   └── requirements.txt
│   └── js/                          # Node scripts (seed, upload GeoJSON)
│       ├── seed-supabase.js
│       ├── seed-supabase-merged.js
│       ├── upload-projects-geojson.js
│       └── upload-projects-merged-geojson.js
├── public/                          # Static assets and data files
│   ├── Images/                      # Logo and branding images
│   ├── *.geojson                    # Geographic data files
│   └── FL_CRE.csv                   # Additional data sources
├── SCALE-R Data/                    # SCALE-R project data
│   ├── Index Data/                  # Risk and resilience indices
│   └── Project Data/                # Project inventory data
├── src/                             # Source code
│   ├── App.jsx                      # Main application component
│   ├── main.jsx                      # Application entry point
│   ├── index.css                    # Global styles
│   ├── utils/                       # Utility functions
│   │   ├── highlightText.jsx        # Text highlighting utility
│   │   ├── searchProjects.js        # Search algorithm
│   │   └── *.test.js                # Unit tests
│   └── test/                        # Test configuration
├── .gitignore                       # Git ignore rules
├── eslint.config.js                 # ESLint configuration
├── index.html                       # HTML entry point
├── package.json                     # Dependencies and scripts
├── vite.config.js                   # Vite configuration
├── vercel.json                      # Vercel deployment config
└── README.md                        # This file
```

### Key Files

- **`src/App.jsx`** - Main application component containing map logic, filters, search, and UI
- **`src/utils/searchProjects.js`** - Search algorithm with relevance scoring
- **`src/utils/highlightText.jsx`** - Text highlighting component for search results
- **`public/project_inventory_database.geojson`** - Primary project data source
- **`public/miami_cities.geojson`** - City and district boundary data
- **`vite.config.js`** - Build configuration and plugin setup

### Data folder layout (scripts)

Python scripts live in `scripts/python/`, Node scripts in `scripts/js/`. They use repo-root-relative paths, so you can run them from any directory. Run Python scripts with `python scripts/python/geocode_lms.py` (etc.); run Node scripts via npm (e.g. `npm run seed-merged`).

- **`data/input/`** — Source CSVs read by scripts: LMS dataset, "Our dataset".
- **`data/output/logs/geocoding/`** — Geocoding outputs: geocoding log, geocoded LMS CSV, duplicate-addresses CSV.
- **`data/output/logs/matched/`** — Matched-project outputs: reference and pairs Excel files.
- **`data/output/merged/`** — Final merged Excel file consumed by `npm run seed-merged`.

## Features in Detail

### Search Functionality

The search system provides intelligent, multi-field searching across all project attributes:

**Searchable Fields:**
- Project name
- City/location
- Infrastructure type
- Project description
- Categories
- Disaster focus

**Features:**
- Case-insensitive matching
- Partial word matching
- Relevance scoring (exact matches ranked higher)
- Real-time results (updates as you type)
- Keyword highlighting in results
- Keyboard navigation support
- Results limited to top 10 most relevant matches

**Usage:**
1. Click or focus on the search bar at the top of the map
2. Type your search query
3. Results appear in a dropdown below the search bar
4. Use arrow keys to navigate, Enter to select, Escape to close
5. Click any result to navigate to that project on the map

### Filtering System

The sidebar provides multiple filtering options that work together:

**Filter Types:**
- **Infrastructure Type**: Green, Blue, Gray, or Hybrid infrastructure
- **Category**: Project categories (e.g., Green Infrastructure, Planning & Assessments)
- **Disaster Focus**: Flooding, Sea Level Rise, Multi-hazard, etc.
- **City**: Filter by specific city or district within Miami-Dade County

**How It Works:**
- Filters are applied in combination (AND logic)
- Markers are dynamically shown/hidden based on active filters
- Active popups for filtered-out projects are automatically closed
- Filter state persists until manually changed

### Map Interactions

**Marker Interactions:**
- Click markers to open detailed project popups
- Hover over markers for visual feedback
- Markers are color-coded by infrastructure type
- Hidden markers (via filters) are automatically managed

**Map Controls:**
- Pan by clicking and dragging
- Zoom with mouse wheel or pinch gestures
- Click outside popups to close them
- Use district navigation to quickly jump to specific areas

**Census Layer:**
- Toggle between Risk Index, Resilience Index, or no layer
- Click census tracts to view detailed risk information
- Hover to see tract statistics
- Layer visibility can be toggled on/off

### Project Popups

Each project popup displays:
- Project name
- Infrastructure type
- Category
- Disaster focus
- City/location
- Project status (with color coding)
- Estimated project cost (formatted)
- Project description (when available)

Popups are positioned dynamically and can be closed by:
- Clicking the close button
- Clicking outside the popup
- Pressing Escape (when search is not active)

## Testing

The project includes comprehensive test coverage for core functionality.

### Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode (re-runs on file changes)
npm test -- --watch

# Run tests with interactive UI
npm run test:ui

# Run tests with coverage report
npm run test:coverage
```

### Test Structure

**Unit Tests:**
- `src/utils/searchProjects.test.js` - Search algorithm tests
  - Edge cases (empty queries, null data)
  - Field-specific searches
  - Relevance scoring
  - Result limiting

- `src/utils/formatCityName.test.js` - City name formatting utility

**Integration Tests:**
- `src/App.search.test.jsx` - Search UI component tests
  - Search bar rendering
  - Results display
  - Clear functionality
  - Keyboard navigation
  - No results handling

### Test Coverage

The test suite covers:
- Search functionality across all fields
- Edge cases and error handling
- UI component rendering
- User interactions
- Data formatting utilities

## Data Sources

### Project Inventory Data

**Primary Source:**
- `public/project_inventory_database.geojson` - Complete project inventory

**Sample Data:**
- `public/project_inventory_database_Sample.geojson` - Sample dataset for testing

**Data Fields:**
- Project name
- Infrastructure type
- Category
- Disaster focus
- City/location
- Project status
- Start/end dates
- Estimated cost
- Project description
- Implementing agency
- Data source links

### Census and Risk Data

**Census Tract Data:**
- `public/censuscommunityresilience.geojson` - Community resilience data
- `SCALE-R Data/Index Data/FEMA_National_Risk_Index.geojson` - FEMA risk index
- `SCALE-R Data/Index Data/vulnerability_index.geojson` - Vulnerability assessments
- `SCALE-R Data/Project Data/community_resilience.geojson` - Community resilience metrics

**Boundary Data:**
- `public/miami_cities.geojson` - City and district boundaries
- `public/Cities.geojson` - Additional city data

### Data Format

All geographic data is provided in GeoJSON format (EPSG:4326 / WGS84). The application automatically handles coordinate system transformations when needed.

## Configuration

### Mapbox Token

The Mapbox access token is configured in `src/App.jsx`:

```javascript
mapboxgl.accessToken = 'pk.eyJ1IjoieW91cnVzZXJuYW1lIiwiYSI6ImNs...';
```

**Security Best Practices:**
- Never commit access tokens to version control
- Use environment variables in production
- Restrict token permissions in Mapbox account settings
- Rotate tokens regularly

### Environment Variables (Recommended)

For production deployments, use environment variables:

1. Create a `.env` file:
```bash
VITE_MAPBOX_TOKEN=your_token_here
```

2. Update `src/App.jsx`:
```javascript
mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN;
```

3. Add `.env` to `.gitignore`

### Customization

**Styling:**
- Global styles: `src/index.css`
- Component styles: Inline styles in `src/App.jsx`
- Map styles: Configured via Mapbox style URLs

**Sidebar Width:**
- Default: 350px
- Location: `src/App.jsx` (search for `width: '350px'`)

**Popup Content:**
- Customize in `MapboxPopup` component in `src/App.jsx`
- Modify `createPopupContent` function for different layouts

## Deployment

### Vercel Deployment

The project is configured for deployment on Vercel with `vercel.json`:

```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

**Deployment Steps:**

1. **Install Vercel CLI** (optional):
```bash
npm i -g vercel
```

2. **Deploy:**
```bash
vercel
```

Or connect your GitHub repository to Vercel for automatic deployments.

3. **Environment Variables:**
   - Add `VITE_MAPBOX_TOKEN` in Vercel dashboard
   - Configure build settings if needed

### Build Configuration

The production build is optimized with:
- Code splitting
- Asset optimization
- Minification
- Tree-shaking

**Build Output:**
- `dist/` directory contains all production assets
- `dist/index.html` - Entry point
- `dist/assets/` - Optimized JavaScript and CSS bundles

### Project data from Supabase Storage

When `VITE_SUPABASE_URL` is set, the app loads project data from Supabase Storage (no DB read per visit). Set up:

1. In Supabase Dashboard: create a **public** Storage bucket named `project-data`.
2. Seed the `projects` table: `npm run seed`. For merged data, place `MergedDataset_OurDB_plus_LMS.xlsx` in `data/output/merged/` and run `npm run seed-merged`.
3. Upload the GeoJSON to Storage: `npm run upload-geojson` (writes `project-data/projects.geojson`).

After any insert/update/delete on `projects`, run `npm run upload-geojson` again, or deploy the Edge Function `regenerate-projects-geojson` and call it from your upload flow so the file updates automatically.

### Add census tract GEOID (`projects_merged_conf1.tract_geoid`)

The source Excel's `FIPSCODE` column mixes city/place codes and zeros — it does not answer "which census tract is this project in?". To get the 11-digit census tract ID (state FIPS + county FIPS + tract code) per project from its coordinates, the repo derives a separate `tract_geoid` value (the original `FIPSCODE` is left untouched).

1. **One-time DB prep** — in Supabase SQL Editor, run [`supabase/sql/add_tract_geoid_column.sql`](supabase/sql/add_tract_geoid_column.sql):

   ```sql
   alter table public.projects_merged_conf1 add column if not exists tract_geoid text;
   ```

2. **Resolve tracts from coordinates** (instant, offline for Miami-Dade):

   ```bash
   pip install -r scripts/python/requirements.txt
   npm run add-tract-geoid
   ```

   Resolution order per row:
   1. **Local point-in-polygon** against `public/censuscommunityresilience.geojson` (706 Miami-Dade tracts; reprojected from Web Mercator on the fly). Handles every point inside the tract layer.
   2. **FCC Census Block API** (`https://geo.fcc.gov/api/census/block/find`) — fallback for points outside the local layer.
   3. **Census Bureau coordinate geocoder** as a last resort (unstable; not relied on).

   Outputs (under `data/output/logs/tract_geoid/`):
   - `projects_with_tract_geoid.csv` — full sheet plus `TRACT_GEOID`, `TRACT_NAME`, `TRACT_LOOKUP_SOURCE`, `TRACT_RESOLVE_STATUS`
   - `tract_geoid_updates.csv` — payload consumed by the sync step
   - `tract_resolve_failures.csv` — only emitted if any rows with coordinates fail every source

   Plus an enriched copy of the merged Excel: `data/output/merged/MergedDataset_Original_plus_LMS_conf1_with_tract_geoid.xlsx`.

3. **Sync the resolved tracts into Supabase** (`projects_merged_conf1.tract_geoid`):

   ```bash
   npm run sync-tract-geoid
   ```

   The sync matches DB rows on `(project_na, lat≈, lng≈)` (with `(project_na, city)` as fallback) and updates whenever the new 11-digit value differs from what's stored. Idempotent and safe to re-run.

4. **Refresh GeoJSON for the app**:

   ```bash
   npm run upload-geojson-merged-conf1
   ```

   The output GeoJSON exposes `TRACT_GEOID` in feature properties.

### Other Deployment Platforms

The application can be deployed to any static hosting service:

- **Netlify**: Connect repository or use Netlify CLI
- **GitHub Pages**: Use GitHub Actions for automated builds
- **AWS S3 + CloudFront**: Upload `dist/` folder to S3 bucket
- **Any static host**: Serve the `dist/` directory

## Troubleshooting

### Common Issues

**Map Not Loading:**
- Verify Mapbox access token is correctly set
- Check browser console for error messages
- Ensure token has proper permissions in Mapbox account
- Verify network connectivity

**Search Not Working:**
- Check browser console for JavaScript errors
- Verify GeoJSON data files are loaded correctly
- Ensure `allProjectsData` state is populated

**Markers Not Appearing:**
- Check filter settings in sidebar
- Verify project data contains valid coordinates
- Check browser console for coordinate parsing errors

**Build Errors:**
- Clear `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Clear Vite cache: `rm -rf .vite`
- Verify Node.js version: `node --version` (should be 18+)

**Popup Not Updating:**
- Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
- Check for JavaScript errors in console
- Verify `activeFeature` state updates correctly

### Browser Compatibility

**Supported Browsers:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Required Features:**
- ES6+ JavaScript support
- CSS Grid and Flexbox
- WebGL (for Mapbox GL JS)
- Fetch API

**Mobile Support:**
- Optimized for tablet devices
- Touch gestures supported
- Responsive layout for larger mobile screens

### Performance Optimization

For large datasets:
- Results are limited to top 10 matches
- Markers are dynamically shown/hidden based on filters
- Map layers are loaded on demand
- GeoJSON data is processed efficiently

If experiencing performance issues:
- Reduce dataset size for testing
- Check browser DevTools Performance tab
- Verify Mapbox token rate limits
- Consider data pagination for very large datasets

## Contributing

We welcome contributions to improve the SCALE-R Resilience Dashboard!

### Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Write or update tests as needed
5. Ensure all tests pass: `npm test`
6. Commit your changes: `git commit -m "Add: description of changes"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Open a Pull Request

### Code Style

- Follow existing code patterns and structure
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions focused and single-purpose
- Test your changes thoroughly

### Pull Request Guidelines

- Provide a clear description of changes
- Reference any related issues
- Include screenshots for UI changes
- Ensure all tests pass
- Update documentation as needed

### Development Setup

1. Follow [Installation](#installation) steps
2. Create a branch for your work
3. Make changes and test locally
4. Run tests before committing
5. Submit pull request when ready

## License

This project is currently for internal use. Licensing terms are to be determined.

For questions about licensing, please contact the project maintainers.

## Acknowledgments

### Data Sources

- **FEMA National Risk Index** - Federal Emergency Management Agency
- **SCALE-R Project** - Research collaboration data
- **Miami-Dade County** - Project inventory and geographic data

### Technologies and Libraries

- [React](https://react.dev/) - UI framework
- [Vite](https://vitejs.dev/) - Build tool
- [Mapbox GL JS](https://docs.mapbox.com/mapbox-gl-js/) - Mapping library
- [Recharts](https://recharts.org/) - Charting library
- [Vitest](https://vitest.dev/) - Testing framework

### Project Support

This project is part of the SCALE-R (Scalable Climate Adaptation and Resilience) research initiative focused on climate resilience planning and infrastructure investment analysis in Miami-Dade County.

---

**For questions, issues, or contributions, please open an issue or pull request on GitHub.**
