async function getKeyFromPassword(password, salt) {
    const encoder = new TextEncoder();
    const keyMaterial = await window.crypto.subtle.importKey(
        "raw",
        encoder.encode(password),
        "PBKDF2",
        false,
        ["deriveKey"]
    );

    return window.crypto.subtle.deriveKey(
        {
            name: "PBKDF2",
            salt: salt,
            iterations: 100000,
            hash: "SHA-256"
        },
        keyMaterial,
        {
            name: "AES-GCM",
            length: 256
        },
        false,
        ["encrypt", "decrypt"]
    );
}

async function encryptString(plainText, password) {
    const encoder = new TextEncoder();
    const salt = window.crypto.getRandomValues(new Uint8Array(16));
    const iv = window.crypto.getRandomValues(new Uint8Array(12));

    const key = await getKeyFromPassword(password, salt);

    const cipherText = await window.crypto.subtle.encrypt(
        {
            name: "AES-GCM",
            iv: iv
        },
        key,
        encoder.encode(plainText)
    );

    // Combine salt, iv, and ciphertext for easy storage
    const combinedBuffer = new Uint8Array(salt.byteLength + iv.byteLength + cipherText.byteLength);
    combinedBuffer.set(salt, 0);
    combinedBuffer.set(iv, salt.byteLength);
    combinedBuffer.set(new Uint8Array(cipherText), salt.byteLength + iv.byteLength);

    return btoa(String.fromCharCode.apply(null, combinedBuffer)); // Convert to base64 for storage/transmission
}

document.getElementById("submit").onclick = async (evt) => {
    evt.preventDefault();

    var content = document.getElementById("content").value.trim();
    const password = document.getElementById("stash-password").value.trim();

    if (content.length === 0) {
        alert("Content cannot be empty");
        return;
    }

    var protected = false;

    if (password.length > 0) {
        content = await encryptString(content, password);
        protected = true;
    }

    const data = {
        owner_id: 0,
        content: content,
        protected: protected
    };

    console.log(JSON.stringify(data));

    fetch("/upload", {
        method: "POST",
        body: JSON.stringify(data),
        headers: {
            "Content-Type": "application/json"
        }
    }).then((response) => {
        if (response.ok) {
            return response.json();
        }
    }).then((data) => {
        document.location.assign(data.id);
    });
}

const passwordFormContainer = document.getElementById("password-form-container");
const stashPasswordInput = document.getElementById("stash-password");

var currentStashPassword = "";

document.getElementById("lock-button").onclick = () => {
    passwordFormContainer.classList.toggle("hidden");

    if (!passwordFormContainer.classList.contains("hidden")) {
        stashPasswordInput.focus();
        currentStashPassword = stashPasswordInput.value;
    }
};

document.getElementById("password-form-save").onclick = () => {
    passwordFormContainer.classList.toggle("hidden");
}

document.getElementById("password-form-close-area").onclick = () => {
    passwordFormContainer.classList.toggle("hidden");
};

document.getElementById("password-form-cancel").onclick = () => {
    passwordFormContainer.classList.toggle("hidden");
    stashPasswordInput.value = currentStashPassword;
}

function generatePassword() {
    var upperCase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    var lowerCase = "abcdefghijklmnopqrstuvwxyz";
    var numbers = "0123456789";
    var specialCharacters = "!@#$%^&*()";

    // Combine all possible characters
    var allCharacters = upperCase + lowerCase + numbers + specialCharacters;

    var passwordLength = 9;
    var password = '';

    // Generate the password
    for (var i = 0; i < passwordLength; i++) {
        var randomIndex = Math.floor(Math.random() * allCharacters.length);
        password += allCharacters[randomIndex];
    }

    return password;
}

document.getElementById("generate-password").onclick = () => {
    document.getElementById("stash-password").value = generatePassword();
}

document.getElementById("content").focus();