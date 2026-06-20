
// ======================================================
// Elements
// ======================================================

const fileInput = document.getElementById("pdfFile");

const uploadStatus = document.getElementById("uploadStatus");

const questionInput = document.getElementById("questionInput");

const chatBox = document.getElementById("chatBox");

const askButton = document.getElementById("askButton");

// ======================================================
// Escape HTML (Security)
// ======================================================

function escapeHTML(text) {

    const div = document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}


// ======================================================
// Scroll Chat Bottom
// ======================================================

function scrollToBottom() {

    chatBox.scrollTop = chatBox.scrollHeight;
}


// ======================================================
// Add Chat Message
// ======================================================

function addMessage(type, content) {

    const div = document.createElement("div");

    div.className = type === "user"
        ? "user-message"
        : "bot-message";

    div.innerHTML = escapeHTML(content);

    chatBox.appendChild(div);

    scrollToBottom();

    return div;
}


// ======================================================
// Upload PDF
// ======================================================

async function uploadPDF() {

    const file = fileInput.files[0];

    if (!file) {

        uploadStatus.innerHTML = `
            <div class="alert alert-danger">
                Please select a PDF file
            </div>
        `;

        return;
    }

    if (!file.name.toLowerCase().endsWith(".pdf")) {

        uploadStatus.innerHTML = `
            <div class="alert alert-danger">
                Only PDF files are allowed
            </div>
        `;

        return;
    }

    const formData = new FormData();

    formData.append("file", file);

    uploadStatus.innerHTML = `
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

        if (response.status === 401) {
            window.location.assign("/login");
            return;
        }

        if (response.ok && data.success) {

            uploadStatus.innerHTML = `
                <div class="alert alert-success">
                    PDF uploaded successfully
                    <br>
                    Chunks Created: ${data.chunks_created}
                </div>
            `;

        } else {

            uploadStatus.innerHTML = `
                <div class="alert alert-danger">
                    ${escapeHTML(data.message)}
                </div>
            `;
        }

    } catch (error) {

        uploadStatus.innerHTML = `
            <div class="alert alert-danger">
                Upload failed
            </div>
        `;

        console.error(error);
    }
}


// ======================================================
// Ask Question
// ======================================================

async function askQuestion() {

    const question = questionInput.value.trim();

    if (!question) {
        return;
    }

    // Disable Button

    askButton.disabled = true;

    // User Message

    addMessage("user", question);

    questionInput.value = "";

    // Loading Message

    const loadingDiv = addMessage(
        "bot",
        "AI is thinking..."
    );

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

        if (response.status === 401) {
            window.location.assign("/login");
            return;
        }

        // Remove Loading

        loadingDiv.remove();

        // Error Response

        if (!response.ok || !data.success) {

            addMessage(
                "bot",
                data.message || "Something went wrong"
            );

            return;
        }

        // Bot Message

        addMessage(
            "bot",
            data.answer || "No answer generated"
        );

        // Sources

        if (data.sources?.length) {

            const sourceDiv = document.createElement("div");

            sourceDiv.className = "source-box";

            sourceDiv.innerHTML = `
                <strong>Sources:</strong>
                <ul>
                    ${data.sources.map(source => `
                        <li>
                            ${escapeHTML(source.source)}
                            (Page: ${source.page})
                        </li>
                    `).join("")}
                </ul>
            `;

            chatBox.appendChild(sourceDiv);

            scrollToBottom();
        }

    } catch (error) {

        loadingDiv.remove();

        addMessage(
            "bot",
            "Something went wrong"
        );

        console.error(error);

    } finally {

        askButton.disabled = false;

        questionInput.focus();
    }
}


// ======================================================
// Enter Key Support
// ======================================================

questionInput.addEventListener(
    "keypress",
    function(event) {

        if (event.key === "Enter") {

            askQuestion();
        }
    }
);
