const API_URL = "http://127.0.0.1:5000/api";


// --------------------------------------------------
// CREATE DEPARTMENT
// --------------------------------------------------

async function createDepartment() {

    const name =
        document.getElementById("name").value;

    const description =
        document.getElementById("description").value;

    const contact =
        document.getElementById("contact").value;


    try {

        const response = await fetch(
            `${API_URL}/departments`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    name: name,
                    description: description,
                    contact: contact
                })
            }
        );


        const data = await response.json();

        alert(data.message || data.error);

        loadDepartments();

    } catch (error) {

        alert("Unable to connect to API Gateway.");

        console.error(error);
    }
}


// --------------------------------------------------
// LOAD DEPARTMENTS
// --------------------------------------------------

async function loadDepartments() {

    try {

        const response =
            await fetch(`${API_URL}/departments`);

        const departments =
            await response.json();


        const container =
            document.getElementById("departments");

        container.innerHTML = "";


        if (!response.ok) {

            container.innerHTML = `
                <p>${departments.error || "Unable to load departments."}</p>
            `;

            return;
        }


        departments.forEach(department => {

            const div =
                document.createElement("div");

            div.className = "department";

            div.innerHTML = `
                <h3>${department.name}</h3>

                <p>ID: ${department.id}</p>

                <p>${department.description || ""}</p>

                <p>Contact: ${department.contact || ""}</p>
            `;

            container.appendChild(div);
        });

    } catch (error) {

        document.getElementById("departments").innerHTML = `
            <p>Unable to connect to API Gateway.</p>
        `;

        console.error(error);
    }
}


// --------------------------------------------------
// LOAD COMPLAINTS FOR DEPARTMENT
// --------------------------------------------------

async function loadComplaints() {

    const id =
        document.getElementById("departmentId").value;


    if (!id) {

        document.getElementById("details").textContent =
            "Please enter a Department ID.";

        return;
    }


    try {

        const response =
            await fetch(
                `${API_URL}/departments/${id}/complaints`
            );


        const data =
            await response.json();


        document.getElementById("details").textContent =
            JSON.stringify(data, null, 2);

    } catch (error) {

        document.getElementById("details").textContent =
            "Unable to connect to API Gateway.";

        console.error(error);
    }
}


// --------------------------------------------------
// LOAD CITIZENS FOR DEPARTMENT
// --------------------------------------------------

async function loadCitizens() {

    const id =
        document.getElementById("departmentId").value;


    if (!id) {

        document.getElementById("details").textContent =
            "Please enter a Department ID.";

        return;
    }


    try {

        const response =
            await fetch(
                `${API_URL}/departments/${id}/citizens`
            );


        const data =
            await response.json();


        document.getElementById("details").textContent =
            JSON.stringify(data, null, 2);

    } catch (error) {

        document.getElementById("details").textContent =
            "Unable to connect to API Gateway.";

        console.error(error);
    }
}