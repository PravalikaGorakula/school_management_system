document.addEventListener("DOMContentLoaded", function () {

    /* =====================================================
       ELEMENTS
    ====================================================== */

    const mapElement = document.getElementById("studentBusMap");

    const latitudeElement = document.getElementById("latitude");
    const longitudeElement = document.getElementById("longitude");
    const speedElement = document.getElementById("speed");
    const ignitionElement = document.getElementById("ignition");
    const tripStatusElement = document.getElementById("tripStatus");
    const lastUpdateElement = document.getElementById("lastUpdate");
    const currentStopElement = document.getElementById("currentStop");
    const nextStopElement = document.getElementById("nextStop");
    const trackerStatusElement = document.getElementById("trackerStatus");

    const connectionStatus = document.getElementById("connectionStatus");
    const connectionText = document.getElementById("connectionText");

    const mapLiveBadge = document.getElementById("mapLiveBadge");

    const alertsList = document.getElementById("alertsList");
    const alertCount = document.getElementById("alertCount");


    /* =====================================================
       MAP
    ====================================================== */

    let map = null;
    let busMarker = null;

    if (mapElement) {

        map = L.map("studentBusMap").setView(
            [20.5937, 78.9629],
            5
        );

        L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                maxZoom: 19,
                attribution: "&copy; OpenStreetMap contributors"
            }
        ).addTo(map);
    }


    /* =====================================================
       BUS ICON
    ====================================================== */

    const busIcon = L.divIcon({

        className: "student-live-bus-marker",

        html: `
            <div style="
                width:44px;
                height:44px;
                background:#123B63;
                border:4px solid white;
                border-radius:50%;
                display:flex;
                align-items:center;
                justify-content:center;
                color:white;
                font-size:19px;
                box-shadow:0 4px 15px rgba(0,0,0,.25);
            ">
                <i class="fa-solid fa-bus"></i>
            </div>
        `,

        iconSize: [44, 44],
        iconAnchor: [22, 22]
    });


    /* =====================================================
       API URL
    ====================================================== */

    const liveDataUrl =
        "/transport/student/live-bus/data/";


    /* =====================================================
       FORMAT TIME
    ====================================================== */

    function formatTime(value) {

        if (!value) {
            return "--";
        }

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return "--";
        }

        return date.toLocaleTimeString(
            [],
            {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
            }
        );
    }


    /* =====================================================
       CONNECTION STATUS
    ====================================================== */

    function setConnection(online) {

        if (!connectionStatus) {
            return;
        }

        if (online) {

            connectionStatus.style.background =
                "#ECFDF5";

            connectionStatus.style.color =
                "#047857";

            connectionText.textContent =
                "Live Connected";

            if (mapLiveBadge) {
                mapLiveBadge.textContent =
                    "LIVE";
            }

        } else {

            connectionStatus.style.background =
                "#FEF2F2";

            connectionStatus.style.color =
                "#DC2626";

            connectionText.textContent =
                "Tracker Offline";

            if (mapLiveBadge) {
                mapLiveBadge.textContent =
                    "OFFLINE";
            }
        }
    }


    /* =====================================================
       UPDATE MAP
    ====================================================== */

    function updateMap(latitude, longitude) {

        if (!map) {
            return;
        }

        if (
            latitude === null ||
            longitude === null ||
            latitude === undefined ||
            longitude === undefined
        ) {
            return;
        }

        const position = [
            Number(latitude),
            Number(longitude)
        ];


        if (!busMarker) {

            busMarker = L.marker(
                position,
                {
                    icon: busIcon
                }
            ).addTo(map);

            busMarker.bindPopup(
                "<strong>School Bus</strong><br>Live Location"
            );

            map.setView(
                position,
                16
            );

        } else {

            busMarker.setLatLng(
                position
            );

        }
    }


    /* =====================================================
       UPDATE ALERTS
    ====================================================== */

    function updateAlerts(alerts) {

        if (!alertsList) {
            return;
        }

        if (!alerts || alerts.length === 0) {

            alertsList.innerHTML = `
                <div class="no-alerts">

                    <i class="fa-solid fa-circle-check"></i>

                    <div>

                        <strong>
                            No active alerts
                        </strong>

                        <p>
                            Your bus currently has no important alerts.
                        </p>

                    </div>

                </div>
            `;

            if (alertCount) {
                alertCount.textContent = "0";
            }

            return;
        }


        if (alertCount) {
            alertCount.textContent =
                alerts.length;
        }


        alertsList.innerHTML =
            alerts.map(function (alert) {

                let severityClass =
                    "normal";

                if (
                    alert.severity === "High" ||
                    alert.severity === "Critical"
                ) {
                    severityClass =
                        "high";
                }


                return `
                    <div class="alert-item">

                        <div class="alert-icon ${severityClass}">

                            <i class="fa-solid fa-triangle-exclamation"></i>

                        </div>

                        <div class="alert-content">

                            <strong>
                                ${escapeHtml(alert.title)}
                            </strong>

                            <p>
                                ${escapeHtml(alert.message)}
                            </p>

                            <span>
                                ${escapeHtml(alert.created_at)}
                            </span>

                        </div>

                    </div>
                `;

            }).join("");
    }


    /* =====================================================
       ESCAPE HTML
    ====================================================== */

    function escapeHtml(value) {

        if (value === null || value === undefined) {
            return "";
        }

        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }


    /* =====================================================
       LOAD LIVE DATA
    ====================================================== */

    async function loadLiveBusData() {

        try {

            const response =
                await fetch(
                    liveDataUrl,
                    {
                        method: "GET",
                        headers: {
                            "X-Requested-With":
                                "XMLHttpRequest"
                        },
                        cache: "no-store"
                    }
                );


            if (!response.ok) {
                throw new Error(
                    "Live bus API failed"
                );
            }


            const data =
                await response.json();


            if (!data.success) {

                setConnection(false);

                return;
            }


            const location =
                data.location || {};

            const trip =
                data.trip || {};


            /* =============================================
               CONNECTION
            ============================================== */

            setConnection(
                Boolean(
                    location.tracker_online
                )
            );


            /* =============================================
               SPEED
            ============================================== */

            if (
                speedElement
            ) {

                speedElement.textContent =
                    location.speed !== null &&
                    location.speed !== undefined
                        ? Number(
                            location.speed
                        ).toFixed(1)
                        : "--";
            }


            /* =============================================
               IGNITION
            ============================================== */

            if (
                ignitionElement
            ) {

                if (
                    location.ignition === true
                ) {

                    ignitionElement.textContent =
                        "ON";

                } else if (
                    location.ignition === false
                ) {

                    ignitionElement.textContent =
                        "OFF";

                } else {

                    ignitionElement.textContent =
                        "Unknown";
                }
            }


            /* =============================================
               COORDINATES
            ============================================== */

            if (
                latitudeElement
            ) {

                latitudeElement.textContent =
                    location.latitude !== null &&
                    location.latitude !== undefined
                        ? Number(
                            location.latitude
                        ).toFixed(6)
                        : "--";
            }


            if (
                longitudeElement
            ) {

                longitudeElement.textContent =
                    location.longitude !== null &&
                    location.longitude !== undefined
                        ? Number(
                            location.longitude
                        ).toFixed(6)
                        : "--";
            }


            /* =============================================
               MAP
            ============================================== */

            updateMap(
                location.latitude,
                location.longitude
            );


            /* =============================================
               TRIP STATUS
            ============================================== */

            if (
                tripStatusElement
            ) {

                tripStatusElement.textContent =
                    trip.status ||
                    "No active trip";
            }


            /* =============================================
               CURRENT STOP
            ============================================== */

            if (
                currentStopElement
            ) {

                currentStopElement.textContent =
                    trip.current_stop ||
                    "Not available";
            }


            /* =============================================
               NEXT STOP
            ============================================== */

            if (
                nextStopElement
            ) {

                nextStopElement.textContent =
                    trip.next_stop ||
                    "--";
            }


            /* =============================================
               LAST UPDATE
            ============================================== */

            if (
                lastUpdateElement
            ) {

                lastUpdateElement.textContent =
                    formatTime(
                        location.last_update ||
                        location.gps_timestamp
                    );
            }


            /* =============================================
               TRACKER STATUS
            ============================================== */

            if (
                trackerStatusElement
            ) {

                trackerStatusElement.textContent =
                    location.tracker_online
                        ? "Online"
                        : "Offline";
            }


            /* =============================================
               ALERTS
            ============================================== */

            updateAlerts(
                data.alerts || []
            );

        }

        catch (error) {

            console.error(
                "Live Bus Error:",
                error
            );

            setConnection(false);

            if (
                trackerStatusElement
            ) {

                trackerStatusElement.textContent =
                    "Connection Error";
            }
        }
    }


    /* =====================================================
       FIRST LOAD
    ====================================================== */

    loadLiveBusData();


    /* =====================================================
       AUTO REFRESH
       EVERY 10 SECONDS
    ====================================================== */

    setInterval(
        loadLiveBusData,
        10000
    );

});