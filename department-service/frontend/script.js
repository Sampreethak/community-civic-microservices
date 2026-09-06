const API_URL = "http://127.0.0.1:5003";


async function createDepartment() {

    const name =
        document.getElementById("name").value;

    const description =
        document.getElementById("description").value;

    const contact =
        document.getElementById("contact").value;


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
}


async function loadDepartments() {

    const response =
        await fetch(`${API_URL}/departments`);

    const departments =
        await response.json();


    const container =
        document.getElementById("departments");

    container.innerHTML = "";


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
}


async function loadComplaints() {

    const id =
        document.getElementById("departmentId").value;


    const response =
        await fetch(
            `${API_URL}/departments/${id}/complaints`
        );


    const data =
        await response.json();


    document.getElementById("details").textContent =
        JSON.stringify(data, null, 2);
}


async function loadCitizens() {

    const id =
        document.getElementById("departmentId").value;


    const response =
        await fetch(
            `${API_URL}/departments/${id}/citizens`
        );


    const data =
        await response.json();


    document.getElementById("details").textContent =
        JSON.stringify(data, null, 2);
}