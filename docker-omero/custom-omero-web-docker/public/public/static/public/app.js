

// Construct the API projects URL
var projectsUrl = PARAMS.API_BASE_URL + 'm/projects/';

// Filter projects by Owner to only show 'your' projects
//projectsUrl += '?owner=' + PARAMS.EXP_ID;


let projectCount = 0;
let datasetCount = 0;
let imageCount = 0;

fetch(projectsUrl)
    .then(rsp => rsp.json())
    .then(data => {
        projectCount = data.meta.totalCount;
        updateSummary();

        let projects = data.data;

        document.getElementById('projects').innerHTML = '';

        projects.forEach(project => {
            // Add project details
            let projectHtml = document.createElement('div');
            projectHtml.classList.add('panel', 'panel-default');
            projectHtml.innerHTML = `
                    <div class="panel-heading" style="font-weight: bold;">${project.Name}</div>`;

            document.getElementById('projects').appendChild(projectHtml);

            // Fetch datasets for each project
            let datasetsUrl = projectsUrl + project['@id'] + '/datasets/';
            fetch(datasetsUrl)
                .then(rsp => rsp.json())
                .then(datasetData => {

                    datasetCount += datasetData.meta.totalCount;
                    updateSummary();

                    let datasets = datasetData.data;


                    // Render datasets under the project
                    if (datasets.length > 0) {
                        let datasetsUnorderedList = document.createElement('ul');
                        datasetsUnorderedList.classList.add('list-group');
                        projectHtml.appendChild(datasetsUnorderedList);

                        datasets.forEach(dataset => {
                            let datasetListItem = document.createElement('li');
                            datasetListItem.classList.add('list-group-item');
                            datasetListItem.innerHTML = `<a href="${PARAMS.SHOW_DATASET_URL}${dataset['@id']}">
                                   ${dataset.Name}
                                </a>`;
                            datasetsUnorderedList.appendChild(datasetListItem);


                            fetch(`${PARAMS.API_BASE_URL}m/datasets/${dataset['@id']}/images/`)
                                .then(rsp => rsp.json())
                                .then(imageData => {
                                    imageCount += imageData.meta.totalCount;
                                    updateSummary();
                                });
                        });
                    } else {
                        let noDatasetHtml = document.createElement('div');
                        noDatasetHtml.innerText = 'No datasets found for this project.';
                        projectHtml.appendChild(noDatasetHtml);
                    }
                });
        });
    });


function updateSummary() {
    let summary = `${projectCount} projects, ${datasetCount} datasets, ${imageCount} images`;
    document.getElementById('summary').innerText = summary;
}