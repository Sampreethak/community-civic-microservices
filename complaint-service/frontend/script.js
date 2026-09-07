const API_URL = "http://127.0.0.1:5002";


// --------------------------------------------------
// SUBMIT COMPLAINT
// --------------------------------------------------

document
    .getElementById("complaintForm")
    .addEventListener("submit", async function(event) {

        event.preventDefault();

        const citizenId =
            document.getElementById("citizenId").value;

        const departmentId =
            document.getElementById("departmentId").value;

        const description =
            document.getElementById("description").value;

        const location =
            document.getElementById("location").value;

        try {

            const response = await fetch(
                `${API_URL}/complaints`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        citizen_id: Number(citizenId),
                        department_id: Number(departmentId),
                        description: description,
                        location: location
                    })
                }
            );

            const data = await response.json();

            const result =
                document.getElementById("result");

            if (response.ok) {

                result.innerHTML = `
                    <h3>Complaint Submitted Successfully</h3>

                    <p>
                        <strong>Complaint ID:</strong>
                        ${data.complaint.complaint_id}
                    </p>

                    <p>
                        <strong>Citizen:</strong>
                        ${data.complaint.citizen_name}
                    </p>

                    <p>
                        <strong>Department:</strong>
                        ${data.complaint.department_name}
                    </p>

                    <p>
                        <strong>Description:</strong>
                        ${data.complaint.description}
                    </p>

                    <p>
                        <strong>Location:</strong>
                        ${data.complaint.location}
                    </p>

                    <p>
                        <strong>Status:</strong>
                        ${data.complaint.status}
                    </p>
                `;

                // Clear form
                document.getElementById("complaintForm").reset();

            } else {

                result.innerHTML = `
                    <h3>Error</h3>
                    <p>${data.error || "Unable to submit complaint"}</p>
                `;
            }

        } catch (error) {

            document.getElementById("result").innerHTML = `
                <h3>Error</h3>
                <p>
                    Complaint Service is unavailable.
                    Please make sure the backend is running on port 5002.
                </p>
            `;

            console.error(error);
        }

    });


// --------------------------------------------------
// TRACK COMPLAINT
// --------------------------------------------------

async function findComplaint() {

    const complaintId =
        document.getElementById("searchComplaintId").value;

    if (!complaintId) {

        document.getElementById("complaintDetails").innerHTML = `
            <p>Please enter a Complaint ID.</p>
        `;

        return;
    }

    try {

        const response = await fetch(
            `${API_URL}/complaints/${complaintId}`
        );

        const data = await response.json();

        const details =
            document.getElementById("complaintDetails");

        if (response.ok) {

            details.innerHTML = `
                <h3>Complaint Details</h3>

                <p>
                    <strong>Complaint ID:</strong>
                    ${data.complaint_id}
                </p>

                <p>
                    <strong>Citizen ID:</strong>
                    ${data.citizen_id}
                </p>

                <p>
                    <strong>Department ID:</strong>
                    ${data.department_id}
                </p>

                <p>
                    <strong>Description:</strong>
                    ${data.description}
                </p>

                <p>
                    <strong>Location:</strong>
                    ${data.location}
                </p>

                <p>
                    <strong>Status:</strong>
                    ${data.status}
                </p>
            `;

        } else {

            details.innerHTML = `
                <p>
                    ${data.error || "Complaint not found"}
                </p>
            `;
        }

    } catch (error) {

        document.getElementById("complaintDetails").innerHTML = `
            <p>
                Complaint Service is unavailable.
            </p>
        `;

        console.error(error);
    }
}