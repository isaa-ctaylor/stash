document.getElementById("submit").onclick = async (evt) => {
    evt.preventDefault();

    const password = document.getElementById("password").value.trim();

    if (password.length === 0) {
        alert("Password cannot be empty");
        return;
    }

    fetch(window.location.pathname + "?" + new URLSearchParams({ raw: 1 }).toString(), {
        method: "GET",
        headers: {
            "Authorization": "Bearer " + password
        }
    }).then((response) => {
        if (response.ok) {
            return response.json();
        }
    }).then((data) => {
        document.getElementById("content").innerHTML = data.content;
        document.getElementById("stash-password-input").style.display = "none";
    });
}