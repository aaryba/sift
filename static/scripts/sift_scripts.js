function searchUsers(is_for_trends) {
    const query = document.getElementById('search').value;
    // alert(query)
    fetch(`/search?query=${query}`)
        .then(response => response.json())
        .then(data => {
            //alert(JSON.stringify(data));
            const results = document.getElementById('results');
            scorllIDInView('results');

            if (is_for_trends == 'true') {

                const tableHeader = document.querySelector('thead');
                tableHeader.innerHTML = `<tr>
                    <th>Email</th>
                    <th>Click Checkmark to see charts</th>
                </tr>`;

                const tableBody = document.querySelector('tbody');
                tableBody.innerHTML = '';


                data.forEach(user_found => {
                    const row = document.createElement('tr');

                    const col1 = document.createElement('td');
                    col1.textContent = user_found.email;

                    const col2 = document.createElement('td');
                    col2.innerHTML = ` <img src="/static/greencheck_s.png" class="icon" data-toggle="tooltip" data-placement="top" title="Click this to see the students Trendline!"  onclick="getTrendImage_student(${user_found.id})" )"> `



                    row.appendChild(col1);
                    row.appendChild(col2);

                    tableBody.appendChild(row);
                });


            }
            else {

                const tableHeader = document.querySelector('thead');
                tableHeader.innerHTML = `<tr>
                <th>Email</th>
                <th>Click Icons to Vote</th>
                </tr>`;

                const tableBody = document.querySelector('tbody');
                tableBody.innerHTML = '';

                // //sample list of lists
                // const myArray = [
                //     ['Row 1, Col 1', 'Row 1, Col 2'],
                //     ['Row 2, Col 1', 'Row 2, Col 2'],
                //     ['Row 3, Col 1', 'Row 3, Col 2']
                // ];

                // myArray.forEach(item => {
                //     const row = document.createElement('tr');
                //     item.forEach(col => {
                //         const cell = document.createElement('td');
                //         cell.textContent = col;
                //         row.appendChild(cell);
                //     });
                //     tableBody.appendChild(row);
                // })

                data.forEach(user_found => {
                    const row = document.createElement('tr');

                    const col1 = document.createElement('td');
                    col1.textContent = user_found.email;

                    const col2 = document.createElement('td');
                    col2.innerHTML = ` <img src="/static/pos.png" class="icon" data-toggle="tooltip" data-placement="top" title="Click this if your feel this student has shown good citizenship behaviours!"  onclick="vote(${user_found.id}, 1, '${user_found.email}' )">
                    <img src="/static/neg.png" class="icon" data-toggle="tooltip" data-placement="top" title="Click this if your feel this student has shown bullying behaviours!" onclick="vote(${user_found.id}, 2, '${user_found.email}' )">
                    <img src="/static/needs_support.png" class="icon" data-toggle="tooltip" data-placement="top" title="Click this if this student is lonely or not noticed enough!" onclick="vote(${user_found.id}, 3, '${user_found.email}' )">
                    `



                    row.appendChild(col1);
                    row.appendChild(col2);

                    tableBody.appendChild(row);
                });

            }
        });

}


function vote(user_selected_id, votetype, user_selected_email) {
    const formData = new FormData();
    formData.append('user_selected_id', user_selected_id);
    formData.append('vote_type', votetype); //1 is +ve, 2 is -ve and 3 is neutral
    formData.append('user_selected_email', user_selected_email); //1 is +ve, 2 is -ve and 3 is neutral


    fetch('/vote', {
        method: 'POST',
        body: formData
    }).then(response => {


        if (response.ok) {
            // alert('Your vote was recorded.');

            response.text().then(text => {
                showMessage(text);
            });
        }
    });
}


/**
 * Performs a GET request to the specified relative URL and displays the response message.
 * 
 * @param {string} relUrlToCall - The relative URL to make the GET request to.
 */
function justDoGetAndShowMessage(relUrlToCall) {
    fetch(relUrlToCall).then(response => {
        if (response.ok) {
            response.text().then(text => {
                showMessage(text);
            });
        }
    });
}

/**
 * Displays a message in a modal dialog.
 * 
 * @param {string} message - The message to be displayed in the modal.
 */
function showMessage(message) {
    document.getElementById('modalMessage').innerText = message;
    $('#voteModal').modal('show');
}


/**
 * Scrolls the element with the specified ID into view smoothly.
 * 
 * @param {string} id - The ID of the element to scroll into view.
 */
function scorllIDInView(id) {
    const element = document.getElementById(id);
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
}


/**
 * Submits the contact form by fetching the necessary data from the input fields,
 * constructing a query string with the encoded data, and calling a function to perform a GET request
 * to submit the form data and display the response message.
 */
function submitContactForm() {
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const message = document.getElementById('message').value;

    // Construct the query string
    const queryString = `?name=${encodeURIComponent(name)}&email=${encodeURIComponent(email)}&message=${encodeURIComponent(message)}`;



    justDoGetAndShowMessage(`/contact${queryString}`);

}


/**
 * Uploads a file using a POST request to '/upload_students_and_staff'.
 * 
 * Retrieves form data from 'uploadForm' element and sends it via fetch API.
 * Displays success or error message based on the response received.
 */
function uploadFile() {
    const form = document.getElementById('uploadForm');
    const formData = new FormData(form);

    fetch('/upload_students_and_staff', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            // console.log('Success:', data);
            // alert('File uploaded successfully!');
            if (data.status === 'success') {
                showMessage('Success! ' + data.message);
            }
            else {
                showMessage('Sorry, we faced an error! ' + data.message);
            }

        })
        .catch((error) => {
            console.error('Error:', error);
            // alert('File upload failed!');
            showMessage('Sorry, File upload failed, please contact administrator!');
        })
}



/**
 * Unhides a specific HTML element by its ID after hiding all jumbotrons.
 * 
 * @param {string} id - The ID of the HTML element to unhide.
 */
function unhideDivById(id) {
    hideAllJumbotrons()
    var element = document.getElementById(id);
    if (element) {
        element.style.display = 'block'; // or 'flex', 'inline', etc., depending on your layout
    }
}

/**
 * Hides all elements with the class "jumbotron_and_charts" by setting their display property to 'none'.
 */
function hideAllJumbotrons() {
    // Get all elements with class "jumbotron"
    //var jumbotrons = document.querySelectorAll('.jumbotron');
    var jumbotrons = document.querySelectorAll('.jumbotron_and_charts');


    // Loop through each element and hide it
    jumbotrons.forEach(function (jumbotron) {
        jumbotron.style.display = 'none';
    });
}


// To enable bootstrap tooltips on page load
$(document).ready(function () {
    $('[data-toggle="tooltip"]').tooltip();
    $('[data-toggle="popover"]').popover()
});

