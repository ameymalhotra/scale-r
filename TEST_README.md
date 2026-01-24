# Testing Guide

This project includes comprehensive tests for the search functionality in the Climate Resilience Dashboard.

## Test Setup

The project uses:
- **Vitest** - Fast unit test framework
- **React Testing Library** - For testing React components
- **jsdom** - DOM environment for tests

## Running Tests

### Install Dependencies

First, install the testing dependencies:

```bash
npm install
```

### Run All Tests

```bash
npm test
```

### Run Tests in Watch Mode

```bash
npm test -- --watch
```

### Run Tests with UI

```bash
npm run test:ui
```

This opens an interactive UI in your browser to view and run tests.

### Run Tests with Coverage

```bash
npm run test:coverage
```

## Test Files

### Unit Tests

- **`src/utils/searchProjects.test.js`** - Tests for the search algorithm
  - Edge cases (empty queries, null data, etc.)
  - Search by project name
  - Search by city
  - Search by infrastructure type
  - Search by description
  - Search by categories
  - Search by disaster focus
  - Relevance scoring
  - Result limiting (top 10)
  - Multiple field matching

- **`src/utils/formatCityName.test.js`** - Tests for city name formatting utility

### Integration Tests

- **`src/App.search.test.jsx`** - Tests for search UI component
  - Search bar rendering
  - Search results display
  - Clear button functionality
  - No results message
  - Case-insensitive search
  - Project details in results

## Test Structure

### Search Function Tests

The `searchProjects` function is tested for:

1. **Edge Cases**
   - Empty/null/undefined queries
   - Missing or invalid project data
   - Empty features arrays

2. **Search Functionality**
   - Exact and partial matches
   - Case-insensitive matching
   - Multiple field searching (name, city, type, description, categories, disaster focus)

3. **Relevance Scoring**
   - Projects starting with search term get higher scores
   - Results sorted by relevance
   - Top 10 results returned

4. **Field Fallbacks**
   - Handles different property name variations (e.g., `Project_Na` vs `Project Name`)
   - Handles missing fields gracefully

### Component Tests

The search UI component is tested for:

1. **Rendering**
   - Search bar appears after map loads
   - Input field is accessible

2. **User Interactions**
   - Typing updates results
   - Clear button works
   - Results display correctly

3. **Search Results**
   - Shows project name, city, and infrastructure type
   - Handles no results gracefully
   - Case-insensitive search

## Writing New Tests

### Example: Testing a New Search Feature

```javascript
import { describe, it, expect } from 'vitest';
import { searchProjects } from './utils/searchProjects.js';

describe('New Search Feature', () => {
  it('should handle new search criteria', () => {
    const mockData = {
      type: 'FeatureCollection',
      features: [/* your test data */]
    };
    
    const results = searchProjects('query', mockData);
    expect(results).toHaveLength(1);
  });
});
```

### Example: Testing Component Behavior

```javascript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App.jsx';

it('should handle user interaction', async () => {
  const user = userEvent.setup();
  render(<App />);
  
  const input = screen.getByPlaceholderText(/search/i);
  await user.type(input, 'test');
  
  expect(screen.getByText(/test result/i)).toBeInTheDocument();
});
```

## Mocking

The tests mock:
- **mapbox-gl** - Map library (not needed for search tests)
- **fetch API** - For loading GeoJSON data
- **DOM APIs** - Handled by jsdom

## Continuous Integration

To run tests in CI/CD:

```bash
npm test -- --run
```

This runs tests once and exits (no watch mode).

## Troubleshooting

### Tests not running

1. Ensure dependencies are installed: `npm install`
2. Check that Vitest is in devDependencies
3. Verify `vite.config.js` has test configuration

### Mock issues

If mapbox-gl mocks fail, check that the mock structure matches the actual API.

### Async issues

Use `waitFor` from React Testing Library for async operations:

```javascript
await waitFor(() => {
  expect(screen.getByText(/expected text/i)).toBeInTheDocument();
});
```

## Coverage Goals

- **Unit Tests**: >90% coverage for search utilities
- **Integration Tests**: Cover all user-facing search features
- **Edge Cases**: All error conditions tested
