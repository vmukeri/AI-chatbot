// Function to send the message to the backend
function sendMessage() {
    const userInputField = document.getElementById("user-input");
    const userInput = userInputField.value.trim();
    if (!userInput) return;

    // Append user's message
    appendMessage('You', userInput);

    // Clear the input field
    userInputField.value = "";

    // Send to backend
    fetch("/ask", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ question: userInput })
    })
    .then(response => response.json())
    .then(data => {
        if (data.answer) {
            appendMessage('AI', data.answer);
        } else {
            appendMessage('AI', 'No response received.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        appendMessage('AI', 'Sorry, there was an error. Please try again.');
    });
}

// Function to append messages to the chat log
function appendMessage(sender, message) {
    const chatLog = document.getElementById("chat-log");
    const messageElement = document.createElement("div");
    messageElement.classList.add("chat-entry");
    messageElement.innerHTML = `<p><strong>${sender}:</strong> ${message}</p>`;
    chatLog.appendChild(messageElement);
    chatLog.scrollTop = chatLog.scrollHeight;
}

// Voice recognition support
function startVoiceRecognition() {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        alert("Your browser doesn't support voice recognition.");
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.start();

    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        document.getElementById("user-input").value = transcript;
        sendMessage(); // Automatically send after recognition
    };

    recognition.onerror = function(event) {
        console.error("Speech recognition error:", event.error);
        appendMessage('AI', 'Voice recognition failed. Try again.');
    };
}

// Handle logout and redirect to thank-you page
function logout() {
    fetch('/logout')
        .then(() => window.location.href = '/thank_you')
        .catch(error => console.error('Logout error:', error));
}

// Form validation
function validateForm() {
    const username = document.getElementById("username").value.trim();
    const email = document.getElementById("email").value.trim();

    const usernameRegex = /^[A-Za-z0-9]+$/;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!usernameRegex.test(username)) {
        alert("Username must be alphanumeric (letters and numbers only).");
        return false;
    }

    if (!emailRegex.test(email)) {
        alert("Please enter a valid email address.");
        return false;
    }

    return true;
}

function uploadFile() {
    const fileInput = document.getElementById("file-input");
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    fetch("/upload", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.content) {
            document.getElementById("user-input").value = data.content.slice(0, 500);  // Optional: limit to 500 chars
        } else {
            alert(data.error || "Upload failed");
        }
    })
    .catch(err => {
        console.error("Upload error:", err);
    });
}




// Optional: Attach Enter keypress to send message
document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("user-input");
    input.addEventListener("keypress", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            sendMessage();
        }
    });
});
