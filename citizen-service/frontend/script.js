const API_URL = "http://localhost:5001";

document.getElementById("citizenForm")
    .addEventListener("submit", async function(event) {

        event.preventDefault();

        const name = document.getElementById("name").value;
        const ward = document.getElementById("ward").value;
        const phone = document.getElementById("phone").value;

        const response = await fetch(API_URL + "/citizens", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name,
                ward,
                phone
            })
        });

        const data = await response.json();

        document.getElementById("result").innerHTML = `
            <h3>Registration Successful</h3>
            Citizen ID: ${data.citizen_id}<br>
            Name: ${data.name}<br>
            Ward: ${data.ward}
        `;
    });


async function findCitizen() {

    const id = document.getElementById("searchId").value;

    const response = await fetch(API_URL + "/citizens/" + id);

    const data = await response.json();

    if (response.ok) {

        document.getElementById("citizenDetails").innerHTML = `
            <h3>Citizen Details</h3>
            ID: ${data.citizen_id}<br>
            Name: ${data.name}<br>
            Ward: ${data.ward}<br>
            Phone: ${data.phone}
        `;

    } else {

        document.getElementById("citizenDetails").innerHTML = data.error;
    }
}