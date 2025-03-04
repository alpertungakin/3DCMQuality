// script.js

document.addEventListener("DOMContentLoaded", function() {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const processBtn = document.getElementById('processBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const optionSelect = document.getElementById('optionSelect');
    const modelViewer = document.getElementById('modelViewer');
    const responseText = document.getElementById('responseText');
    const responseLoader = document.getElementById('responseLoader');
    const visualizeBtn = document.getElementById('visualizeBtn');
    const responseRdf = { text: "not yet" };;

    function showDownload(){
        downloadBtn.style.visibility = "visible";
        visualizeBtn.style.visibility = "visible";
    }

    function showLoader(){
        responseLoader.style.visibility = "visible";
    }

    function hideLoader(){
        responseLoader.style.visibility = "hidden";
    }

    function loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve; // Resolve the promise when the script is loaded
            script.onerror = reject; // Reject the promise if the script fails to load
            document.head.appendChild(script);
        });
    }

    let cityjson = null;

    uploadBtn.addEventListener('click', function() {
        const file = fileInput.files[0];
        if (file) {
            const formData = new FormData();
            formData.append('file', file);

            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.text())
            .then(data => {
                cityjson = data;
                responseText.textContent = "File uploaded successfully.";
                responseText.style.color = "green";
            })
            .catch(error => {
                responseText.textContent = "Error uploading file.";
                responseText.style.color = "red";
            });
        } else {
            responseText.textContent = "Please select a file to upload.";
            responseText.style.color = "red";
        }
    });

    processBtn.addEventListener('click', function() {
        const selectedOption = optionSelect.value;

        if (!cityjson) {
            responseText.textContent = "Please upload a CityJSON file.";
            responseText.style.color = "red";
            return;
        }

        const formData = new FormData();
        formData.append('cityjson', cityjson);
        formData.append('ontology', selectedOption);

        showLoader();
        fetch('/process_texts', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            responseText.textContent = data.response;
            responseRdf.text = data.rdf;
            console.log(responseRdf.text)
            hideLoader();
            showDownload();
            responseText.style.color = "green";
        })
        .catch(error => {
            console.error("Error details:", error.message);
            responseText.textContent = "Error processing data.";
            responseText.style.color = "red";
        });
    });

    downloadBtn.addEventListener('click', function() {
        if (responseText.textContent.includes("Validation Report")) {
            const reportContent = responseText.textContent;

            const blob = new Blob([reportContent], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'report.txt';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } else {
            responseText.textContent = "Please process the data before downloading the report.";
            responseText.style.color = "red";
        }
    });

    visualizeBtn.addEventListener('click', function() {
        if (responseText.textContent.includes("Validation Report")) {
            // Prepare the data to send
            const payload = {
                shacl: responseText.textContent, // SHACL validation results
                rdf: responseRdf.text // Turtle data
            };
            showLoader();
            // Send the data as JSON
            fetch('/visualize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json', // Set the content type to JSON
                },
                body: JSON.stringify(payload) // Send the data as JSON
            })
            .then(response => response.json())
            .then(data => {
                console.log(data.response); // Handle the response from the server
                hideLoader();
            })
            .catch(error => {
                console.error("Error details:", error.message);
                responseText.textContent = "Error visualizing data.";
                responseText.style.color = "red";
            });
        }
    });
});
