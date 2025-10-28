function fetch_data(){
    fetch('/info')
    .then(response => response.json())
    .then(data => {
        document.getElementById('username').textContent = data.username;
        document.getElementById('firstname').textContent = data.firstname;
        document.getElementById('lastname').textContent = data.lastname;
        document.getElementById('email').textContent = data.email;
    })
}
fetch_data();