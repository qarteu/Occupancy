document.addEventListener("DOMContentLoaded", function () {
    function fetchOccupancy() {
        // Fetch occupancy data from the server
        fetch("/get_occupancy")
            .then(response => response.json())
            .then(data => {
                document.getElementById("occupancy-count").textContent = data.occupancy;
                document.getElementById("max-occupancy").textContent = data.max_occupancy;

                // Show or hide the alert based on occupancy status
                if (data.occupancy >= data.max_occupancy) {
                    document.getElementById("alert").classList.remove("hidden");
                } else {
                    document.getElementById("alert").classList.add("hidden");
                }
            })
            .catch(error => console.error("Error fetching occupancy data:", error));
    }

    // Update occupancy data every 2 seconds
    setInterval(fetchOccupancy, 2000);
});
