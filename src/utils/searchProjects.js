// Search projects across all relevant fields
export const searchProjects = (query, projectsData) => {
  if (!query || !query.trim() || !projectsData?.features) {
    return [];
  }

  const searchTerm = query.trim().toLowerCase();
  const results = [];

  projectsData.features.forEach((feature) => {
    const props = feature.properties || {};
    
    // Extract searchable fields
    const projectName = (props['Project_Na'] || props['Project Name'] || '').toLowerCase();
    const description = (props['New_15_25_'] || props['New 15-25 Words Project Description'] || '').toLowerCase();
    const city = ((props['NAME'] || props['City']) ? (props['NAME'] || props['City']).trim() : (props['NAME'] || props['City']) || '').toLowerCase();
    const infrastructureType = (props['Infrastruc'] || props['Infrastructure Type'] || props['Type'] || '').toLowerCase();
    const categories = (props['Categories'] || '').toLowerCase();
    const disasterFocus = (props['Disaster_F'] || props['Disaster Focus'] || '').toLowerCase();

    // Check if search term matches any field
    const matches = 
      projectName.includes(searchTerm) ||
      description.includes(searchTerm) ||
      city.includes(searchTerm) ||
      infrastructureType.includes(searchTerm) ||
      categories.includes(searchTerm) ||
      disasterFocus.includes(searchTerm);

    if (matches) {
      // Calculate relevance score (exact matches in name get higher score)
      let score = 0;
      if (projectName.startsWith(searchTerm)) score += 10; // Exact start match in name
      else if (projectName.includes(searchTerm)) score += 5; // Partial match in name
      if (description.includes(searchTerm)) score += 2;
      if (city.includes(searchTerm)) score += 3;
      if (infrastructureType.includes(searchTerm)) score += 2;
      if (categories.includes(searchTerm)) score += 1;
      if (disasterFocus.includes(searchTerm)) score += 1;

      results.push({ feature, score });
    }
  });

  // Sort by relevance score (descending) and return top 10
  return results
    .sort((a, b) => b.score - a.score)
    .slice(0, 10)
    .map(item => item.feature);
};
