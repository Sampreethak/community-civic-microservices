const API_URL = "http://localhost:5002";

document.getElementById("complaintForm")
    .addEventListener("submit", async function(event) {

        event.preventDefault();

        const citizenId = document.getElementById("citizenId").value;
        const description = document.getElementById("description").value;
        const location = document.getElementById("location").value;

        const response = await fetch(API_URL + "/complaints", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                citizen_id: citizenId,
                description: description,
                location: location
            })
        });

        const data = await response.json();

        document.getElementById("result").innerHTML =
            `<h3>Complaint Registered</h3>
            Complaint ID: ${data.complaint_id}<br>
            Status: ${data.status}`;
    });


async function findComplaint() {

    const id = document.getElementById("searchComplaintId").value;

    const response = await fetch(API_URL + "/complaints/" + id);

    const data = await response.json();

    if (response.ok) {

        document.getElementById("complaintDetails").innerHTML =
            `<h3>Complaint Details</h3>
            Complaint ID: ${data.complaint_id}<br>
            Citizen ID: ${data.citizen_id}<br>
            Issue: ${data.description}<br>
            Location: ${data.location}<br>
            Status: ${data.status}`;

    } else {

        document.getElementById("complaintDetails").innerHTML = data.error;
    }
}