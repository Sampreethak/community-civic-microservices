const API_URL = "http://127.0.0.1:5000/api";


// --------------------------------------------------
// REGISTER CITIZEN
// --------------------------------------------------

document.getElementById("citizenForm")
    .addEventListener("submit", async function(event) {

        event.preventDefault();

        const name = document.getElementById("name").value;
        const ward = document.getElementById("ward").value;
        const phone = document.getElementById("phone").value;

        try {

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

            if (response.ok) {

                document.getElementById("result").innerHTML = `
                    <h3>Registration Successful</h3>
                    Citizen ID: ${data.citizen_id}<br>
                    Name: ${data.name}<br>
                    Ward: ${data.ward}
                `;

            } else {

                document.getElementById("result").innerHTML = `
                    <h3>Error</h3>
                    ${data.error || "Unable to register citizen"}
                `;
            }

        } catch (error) {

            document.getElementById("result").innerHTML = `
                <h3>Error</h3>
                Citizen Service is unavailable
            `;
        }
    });


// --------------------------------------------------
// FIND CITIZEN
// --------------------------------------------------

async function findCitizen() {

    const id = document.getElementById("searchId").value;

    if (!id) {

        document.getElementById("citizenDetails").innerHTML =
            "Please enter a Citizen ID.";

        return;
    }

    try {

        const response = await fetch(
            API_URL + "/citizens/" + id
        );

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

            document.getElementById("citizenDetails").innerHTML =
                data.error || "Citizen not found.";
        }

    } catch (error) {

        document.getElementById("citizenDetails").innerHTML =
            "Citizen Service is unavailable.";
    }
}