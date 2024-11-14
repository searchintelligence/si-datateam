// Event listener for category change
document.getElementById('category-select').addEventListener('change', function () {
    const categoryId = this.value;
    if (categoryId) {
        const url = `/data_contexts/${categoryId}`;
        htmx.ajax('GET', url, '#context-select');
        // Reset datasets when category changes
        document.getElementById('datasets-select').innerHTML = `
                    <div class="checkbox-group">
                        <input type="checkbox" id="default-dataset" value="" disabled>
                        <label for="default-dataset">Select a context to view available datasets...</label>
                    </div>`;
    } else {
        // Reset contexts and datasets when no category is selected
        document.getElementById('context-select').innerHTML = '<option value="">Select context...</option>';
        document.getElementById('datasets-select').innerHTML = `
                    <div class="checkbox-group">
                        <input type="checkbox" id="default-dataset" value="" disabled>
                        <label for="default-dataset">Select a context to view available datasets...</label>
                    </div>`;
    }
});

// Event listener for context change
document.getElementById('context-select').addEventListener('change', function () {
    const contextId = this.value;
    if (contextId) {
        const categoryId = document.getElementById('category-select').value;
        const url = `/data_sets/${categoryId}/${contextId}`;
        htmx.ajax('GET', url, '#datasets-select');
    } else {
        // Reset datasets when no context is selected
        document.getElementById('datasets-select').innerHTML = `
                    <div class="checkbox-group">
                        <input type="checkbox" id="default-dataset" value="" disabled>
                        <label for="default-dataset">Select a context to view available datasets...</label>
                    </div>`;
    }
});

// Event listener for submit button
document.getElementById('submit-button').addEventListener('click', function () {
    const categoryId = document.getElementById('category-select').value;
    const contextId = document.getElementById('context-select').value;
    const datasetCheckboxes = document.querySelectorAll('#datasets-select input[type="checkbox"]:checked');
    const datasetIds = Array.from(datasetCheckboxes).map(checkbox => checkbox.value);

    if (!categoryId || !contextId || datasetIds.length === 0) {
        alert('Please select a category, context, and at least one dataset.');
        return;
    }

    // Prepare form data
    const formData = new FormData();
    formData.append('context_id', contextId);
    datasetIds.forEach(datasetId => {
        formData.append('datasets', datasetId);
    });

    // Fetch data from the backend
    fetch('/data', {
        method: 'POST',
        body: formData,
    })
        .then(response => response.json())
        .then(data => {
            // Render the data as a table
            renderDataTable(data, datasetIds);

            // Fetch and display citations for selected datasets
            fetchAndDisplayCitations(datasetIds);
        })
        .catch(error => {
            console.error('Error fetching data:', error);
        });
});

// Function to render data as a table
function renderDataTable(data, datasetIds) {
    const resultsContainer = document.getElementById('results-container');
    resultsContainer.innerHTML = ''; // Clear previous results

    // Get the list of datasets (column headers)
    const datasetNames = new Map();
    let index = 1;
    datasetIds.forEach(datasetId => {
        const datasetCheckbox = document.querySelector(`#dataset_${datasetId}`);
        const datasetName = datasetCheckbox ? datasetCheckbox.nextElementSibling.textContent : `Dataset ${datasetId}`;
        datasetNames.set(datasetName, index);
        index++;
    });

    // Create the table
    const table = document.createElement('table');
    table.border = '1';
    table.style.borderCollapse = 'collapse';
    table.style.width = '100%';

    // Create the table header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    const entityHeader = document.createElement('th');
    entityHeader.textContent = 'Entity';
    headerRow.appendChild(entityHeader);

    datasetNames.forEach((num, datasetName) => {
        const th = document.createElement('th');
        th.textContent = `${datasetName} [${num}]`;
        headerRow.appendChild(th);
    });

    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Create the table body
    const tbody = document.createElement('tbody');

    for (const entity in data) {
        const row = document.createElement('tr');
        const entityCell = document.createElement('td');
        entityCell.textContent = entity;
        row.appendChild(entityCell);

        datasetNames.forEach((num, datasetName) => {
            const cell = document.createElement('td');
            cell.textContent = data[entity][datasetName] || 'N/A';
            row.appendChild(cell);
        });

        tbody.appendChild(row);
    }

    table.appendChild(tbody);
    resultsContainer.appendChild(table);
}

// Function to fetch and display citations for selected datasets
function fetchAndDisplayCitations(datasetIds) {
    const citationsContainer = document.getElementById('citations-container');
    citationsContainer.innerHTML = ''; // Clear previous citations

    // Create an array of fetch promises
    const fetchPromises = datasetIds.map(datasetId => {
        return fetch(`/citations/${datasetId}`)
            .then(response => response.json())
            .then(data => {
                return { datasetId, citations: data.citations };
            })
            .catch(error => {
                console.error(`Error fetching citations for dataset ${datasetId}:`, error);
                return { datasetId, citations: [] };
            });
    });

    // Wait for all fetches to complete
    Promise.all(fetchPromises).then(results => {
        // Map to store datasetId to citation mapping with numbers
        const datasetCitationMap = new Map();
        let index = 1;
        results.forEach(result => {
            datasetCitationMap.set(result.datasetId, { index: index, citations: result.citations });
            index++;
        });

        // Display citations in order
        const citationList = document.createElement('ul');

        // Sort the datasetIds based on the assigned index
        const sortedDatasetIds = Array.from(datasetCitationMap.entries()).sort((a, b) => a[1].index - b[1].index);

        sortedDatasetIds.forEach(([datasetId, { index, citations }]) => {
            if (citations.length > 0) {
                citations.forEach(citation => {
                    const citationItem = document.createElement('li');
                    citationItem.style.marginBottom = '10px';
                    citationItem.id = `citation_${index}`;
                    // Format the citation in IEEE style
                    const formattedCitation = `[${index}] ${citation.author}, "${citation.text}," ${citation.start_date ? citation.start_date.substring(0, 4) : ''}-${citation.end_date ? citation.end_date.substring(0, 4) : ''}, accessed on ${citation.date_accessed ? citation.date_accessed : ''}. Available: ${citation.url}`;
                    citationItem.textContent = formattedCitation;
                    citationList.appendChild(citationItem);
                });
            } else {
                // If no citation available, still show the number
                const citationItem = document.createElement('li');
                citationItem.style.marginBottom = '10px';
                citationItem.id = `citation_${index}`;
                citationItem.textContent = `[${index}] No citation available.`;
                citationList.appendChild(citationItem);
            }
        });

        citationsContainer.appendChild(citationList);
    });
}