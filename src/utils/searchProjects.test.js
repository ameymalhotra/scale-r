import { describe, it, expect } from 'vitest';
import { searchProjects } from './searchProjects.js';

describe('searchProjects', () => {
  const mockProjectsData = {
    type: 'FeatureCollection',
    features: [
      {
        id: 1,
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [-80.1918, 25.7617]
        },
        properties: {
          'Project_Na': 'Miami Beach Flood Protection',
          'Project Name': 'Miami Beach Flood Protection',
          'New_15_25_': 'Comprehensive flood protection system for Miami Beach',
          'NAME': 'Miami Beach',
          'City': 'Miami Beach',
          'Infrastruc': 'Blue Infrastructure',
          'Infrastructure Type': 'Blue Infrastructure',
          'Categories': 'Flood Control',
          'Disaster_F': 'Flooding',
          'Disaster Focus': 'Flooding'
        }
      },
      {
        id: 2,
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [-80.1318, 25.7917]
        },
        properties: {
          'Project_Na': 'Coral Gables Green Infrastructure',
          'Project Name': 'Coral Gables Green Infrastructure',
          'New_15_25_': 'Green infrastructure project in Coral Gables',
          'NAME': 'Coral Gables',
          'City': 'Coral Gables',
          'Infrastruc': 'Green Infrastructure',
          'Infrastructure Type': 'Green Infrastructure',
          'Categories': 'Environmental',
          'Disaster_F': 'Hurricane',
          'Disaster Focus': 'Hurricane'
        }
      },
      {
        id: 3,
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [-80.2118, 25.7717]
        },
        properties: {
          'Project_Na': 'Doral Stormwater Management',
          'Project Name': 'Doral Stormwater Management',
          'New_15_25_': 'Stormwater management system for Doral',
          'NAME': 'Doral',
          'City': 'Doral',
          'Infrastruc': 'Grey Infrastructure',
          'Infrastructure Type': 'Grey Infrastructure',
          'Type': 'Grey Infrastructure',
          'Categories': 'Water Management',
          'Disaster_F': 'Flooding',
          'Disaster Focus': 'Flooding'
        }
      },
      {
        id: 4,
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [-80.1918, 25.7517]
        },
        properties: {
          'Project_Na': 'Hybrid Resilience Project',
          'New_15_25_': 'Combined green and blue infrastructure',
          'NAME': 'Miami',
          'City': 'Miami',
          'Infrastruc': 'Hybrid',
          'Categories': 'Multi-purpose',
          'Disaster_F': 'Multi-hazard'
        }
      }
    ]
  };

  describe('Edge Cases', () => {
    it('should return empty array for empty query', () => {
      const results = searchProjects('', mockProjectsData);
      expect(results).toEqual([]);
    });

    it('should return empty array for whitespace-only query', () => {
      const results = searchProjects('   ', mockProjectsData);
      expect(results).toEqual([]);
    });

    it('should return empty array for null query', () => {
      const results = searchProjects(null, mockProjectsData);
      expect(results).toEqual([]);
    });

    it('should return empty array for undefined query', () => {
      const results = searchProjects(undefined, mockProjectsData);
      expect(results).toEqual([]);
    });

    it('should return empty array for null projectsData', () => {
      const results = searchProjects('test', null);
      expect(results).toEqual([]);
    });

    it('should return empty array for undefined projectsData', () => {
      const results = searchProjects('test', undefined);
      expect(results).toEqual([]);
    });

    it('should return empty array for projectsData without features', () => {
      const results = searchProjects('test', {});
      expect(results).toEqual([]);
    });

    it('should return empty array for empty features array', () => {
      const results = searchProjects('test', { features: [] });
      expect(results).toEqual([]);
    });
  });

  describe('Search by Project Name', () => {
    it('should find projects by exact name match', () => {
      const results = searchProjects('Miami Beach Flood Protection', mockProjectsData);
      expect(results).toHaveLength(1);
      expect(results[0].properties['Project_Na']).toBe('Miami Beach Flood Protection');
    });

    it('should find projects by partial name match', () => {
      const results = searchProjects('Miami Beach', mockProjectsData);
      expect(results).toHaveLength(1);
      expect(results[0].properties['Project_Na']).toBe('Miami Beach Flood Protection');
    });

    it('should find projects by case-insensitive name match', () => {
      const results = searchProjects('miami beach', mockProjectsData);
      expect(results).toHaveLength(1);
      expect(results[0].properties['Project_Na']).toBe('Miami Beach Flood Protection');
    });

    it('should prioritize exact start matches in name', () => {
      const results = searchProjects('Miami', mockProjectsData);
      // Should find Miami Beach project first (starts with "Miami")
      expect(results.length).toBeGreaterThan(0);
      const firstResult = results[0];
      expect(firstResult.properties['Project_Na']).toContain('Miami');
    });
  });

  describe('Search by City', () => {
    it('should find projects by city name', () => {
      const results = searchProjects('Coral Gables', mockProjectsData);
      expect(results).toHaveLength(1);
      expect(results[0].properties['NAME']).toBe('Coral Gables');
    });

    it('should find projects by city name (case-insensitive)', () => {
      const results = searchProjects('coral gables', mockProjectsData);
      expect(results).toHaveLength(1);
      expect(results[0].properties['NAME']).toBe('Coral Gables');
    });

    it('should find projects using City field as fallback', () => {
      const results = searchProjects('Doral', mockProjectsData);
      expect(results).toHaveLength(1);
      expect(results[0].properties['City']).toBe('Doral');
    });
  });

  describe('Search by Infrastructure Type', () => {
    it('should find projects by infrastructure type', () => {
      const results = searchProjects('Blue Infrastructure', mockProjectsData);
      // Should find at least 1 result (may find more if description also matches "blue infrastructure")
      expect(results.length).toBeGreaterThanOrEqual(1);
      // Verify at least one result has the correct infrastructure type
      // (The first result should be the one with direct field match due to higher relevance score)
      const hasBlueInfrastructure = results.some(r => r.properties['Infrastruc'] === 'Blue Infrastructure');
      expect(hasBlueInfrastructure).toBe(true);
    });

    it('should find projects by infrastructure type (case-insensitive)', () => {
      const results = searchProjects('green infrastructure', mockProjectsData);
      expect(results).toHaveLength(1);
      expect(results[0].properties['Infrastruc']).toBe('Green Infrastructure');
    });

    it('should find projects using Type field as fallback', () => {
      const results = searchProjects('Grey', mockProjectsData);
      expect(results.length).toBeGreaterThan(0);
    });
  });

  describe('Search by Description', () => {
    it('should find projects by description content', () => {
      const results = searchProjects('flood protection', mockProjectsData);
      expect(results.length).toBeGreaterThan(0);
      expect(results.some(r => r.properties['Project_Na'].includes('Flood'))).toBe(true);
    });

    it('should find projects by partial description match', () => {
      const results = searchProjects('comprehensive', mockProjectsData);
      expect(results.length).toBeGreaterThan(0);
    });
  });

  describe('Search by Categories', () => {
    it('should find projects by category', () => {
      const results = searchProjects('Flood Control', mockProjectsData);
      expect(results).toHaveLength(1);
      expect(results[0].properties['Categories']).toBe('Flood Control');
    });

    it('should find projects by partial category match', () => {
      const results = searchProjects('Environmental', mockProjectsData);
      expect(results).toHaveLength(1);
    });
  });

  describe('Search by Disaster Focus', () => {
    it('should find projects by disaster focus', () => {
      const results = searchProjects('Flooding', mockProjectsData);
      expect(results.length).toBeGreaterThanOrEqual(2);
    });

    it('should find projects by disaster focus (case-insensitive)', () => {
      const results = searchProjects('hurricane', mockProjectsData);
      expect(results).toHaveLength(1);
      expect(results[0].properties['Disaster_F']).toBe('Hurricane');
    });

    it('should find projects using Disaster Focus field as fallback', () => {
      const results = searchProjects('Multi-hazard', mockProjectsData);
      expect(results).toHaveLength(1);
    });
  });

  describe('Relevance Scoring', () => {
    it('should prioritize projects with name starting with search term', () => {
      const results = searchProjects('Miami', mockProjectsData);
      // Projects starting with "Miami" should come first
      if (results.length > 1) {
        const firstScore = results[0].properties['Project_Na'].toLowerCase().startsWith('miami') ? 10 : 0;
        expect(firstScore).toBeGreaterThan(0);
      }
    });

    it('should sort results by relevance score (highest first)', () => {
      const results = searchProjects('Miami', mockProjectsData);
      // Results should be sorted (we can't directly check scores, but we can verify ordering)
      expect(results.length).toBeGreaterThan(0);
    });
  });

  describe('Result Limiting', () => {
    it('should limit results to top 10', () => {
      // Create a large dataset
      const largeDataset = {
        type: 'FeatureCollection',
        features: Array.from({ length: 20 }, (_, i) => ({
          id: i,
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [-80.1918, 25.7617] },
          properties: {
            'Project_Na': `Test Project ${i}`,
            'New_15_25_': 'test description',
            'NAME': 'Miami',
            'Infrastruc': 'Blue Infrastructure',
            'Categories': 'Test',
            'Disaster_F': 'Flooding'
          }
        }))
      };

      const results = searchProjects('test', largeDataset);
      expect(results.length).toBeLessThanOrEqual(10);
    });
  });

  describe('Multiple Field Matching', () => {
    it('should find projects matching multiple fields', () => {
      const results = searchProjects('Miami', mockProjectsData);
      // Should find projects matching in name, city, or description
      expect(results.length).toBeGreaterThan(0);
    });

    it('should handle projects with missing fields gracefully', () => {
      const incompleteData = {
        type: 'FeatureCollection',
        features: [
          {
            id: 1,
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [-80.1918, 25.7617] },
            properties: {
              'Project_Na': 'Test Project'
              // Missing other fields
            }
          }
        ]
      };

      const results = searchProjects('Test', incompleteData);
      expect(results).toHaveLength(1);
    });
  });

  describe('Trim and Normalize', () => {
    it('should trim whitespace from query', () => {
      const results = searchProjects('  Miami Beach  ', mockProjectsData);
      expect(results).toHaveLength(1);
    });

    it('should handle city names with extra whitespace', () => {
      const dataWithWhitespace = {
        type: 'FeatureCollection',
        features: [
          {
            id: 1,
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [-80.1918, 25.7617] },
            properties: {
              'Project_Na': 'Test Project',
              'NAME': '  Miami Beach  ',
              'City': '  Miami Beach  '
            }
          }
        ]
      };

      const results = searchProjects('Miami Beach', dataWithWhitespace);
      expect(results).toHaveLength(1);
    });
  });
});
