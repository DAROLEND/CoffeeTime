document.addEventListener("DOMContentLoaded", function () {
    const tables = document.querySelectorAll(".table:not(.booked)");
    const selectedInput = document.getElementById("selected_tables");
    const selected = [];

    tables.forEach(table => {
        table.addEventListener("click", () => {
            const number = table.dataset.table;
            if (table.classList.contains("selected")) {
                table.classList.remove("selected");
                const index = selected.indexOf(number);
                if (index > -1) selected.splice(index, 1);
            } else {
                table.classList.add("selected");
                selected.push(number);
            }
            selectedInput.value = selected.join(',');
        });
    });
});
