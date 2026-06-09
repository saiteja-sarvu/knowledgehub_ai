
// ======================================================
// Upload PDF
// ======================================================

async function uploadPDF() {

    const fileInput = document.getElementById("pdfFile");

    const statusDiv = document.getElementById("uploadStatus");

    const file = fileInput.files[0];

    if (!file) {

        statusDiv.innerHTML = `
            <div class="alert alert-danger">
                Please select a PDF file
            </div>
        `;

        return;
    }

    const formData = new FormData();

    formData.append("file", file);

    statusDiv.innerHTML = `
        <div class="alert alert-info">
            Uploading PDF...
        </div>
    `;

    try {

        const response = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
console.log(data);
        if (data.success) {

            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    PDF uploaded successfully
                </div>
            `;

        } else {

            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    ${data.message}
                </div>
            `;
        }

    } catch (error) {

        statusDiv.innerHTML = `
            <div class="alert alert-danger">
                Upload failed
            </div>
        `;
    }
}


// ======================================================
// Ask Question
// ======================================================

async function askQuestion() {

    const input = document.getElementById("questionInput");

    const chatBox = document.getElementById("chatBox");

    const question = input.value.trim();

    if (!question) {
        return;
    }

    // User Message

    chatBox.innerHTML += `
        <div class="user-message">
            ${question}
        </div>
    `;

    input.value = "";

    // Loading

    chatBox.innerHTML += `
        <div class="bot-message" id="loadingMessage">
            AI is thinking...
        </div>
    `;

    chatBox.scrollTop = chatBox.scrollHeight;

    try {

        const response = await fetch("/ask", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                question: question
            })

        });

        const data = await response.json();
console.log(data);
        // Remove Loading

        document
            .getElementById("loadingMessage")
            .remove();

        // Bot Response

        chatBox.innerHTML += `
            <div class="bot-message">
                ${data.answer}
            </div>
        `;

        chatBox.scrollTop = chatBox.scrollHeight;

    } catch (error) {

        document
            .getElementById("loadingMessage")
            .remove();

        chatBox.innerHTML += `
            <div class="bot-message">
                Something went wrong
            </div>
        `;
    }
}


// ======================================================
// Enter Key Support
// ======================================================

document
    .getElementById("questionInput")
    .addEventListener("keypress", function(event) {

        if (event.key === "Enter") {

            askQuestion();
        }

    });
