// script.js

document.addEventListener("DOMContentLoaded", function() {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const processBtn = document.getElementById('processBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const optionSelect = document.getElementById('optionSelect');
    const modelViewer = document.getElementById('modelViewer');
    const responseText = document.getElementById('responseText');

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

        fetch('/process_texts', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            responseText.textContent = data.response;
            console.log(responseText.textContent);
            responseText.style.color = "green";
        })
        .catch(error => {
            responseText.textContent = "Error processing data.";
            responseText.style.color = "red";
        });
    });

    downloadBtn.addEventListener('click', function() {
        if (responseText.textContent.includes("Processed text:")) {
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
});
