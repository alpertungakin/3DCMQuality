document.addEventListener('DOMContentLoaded', () => {
    const optionSelect = document.getElementById('optionSelect');
    const selectedContent = document.getElementById('selectedContent');
    const fileInput = document.getElementById('fileInput');
    const fileContent = document.getElementById('fileContent');
    const uploadBtn = document.getElementById('uploadBtn');
    const processBtn = document.getElementById('processBtn');
    const responseText = document.getElementById('responseText');

    optionSelect.addEventListener('change', () => {
        fetch('/get_content', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `selected_option=${optionSelect.value}`
        })
        .then(response => response.text())
        .then(data => {
            selectedContent.value = data;
        });
    });

    uploadBtn.addEventListener('click', () => {
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.text())
        .then(data => {
            fileContent.value = data;
        });
    });

    processBtn.addEventListener('click', () => {
        const text1 = fileContent.value;
        const text2 = selectedContent.value;

        fetch('/process_texts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `text1=${encodeURIComponent(text1)}&text2=${encodeURIComponent(text2)}`
        })
        .then(response => response.json())
        .then(data => {
            responseText.textContent = data.response;
        });
    });
});
