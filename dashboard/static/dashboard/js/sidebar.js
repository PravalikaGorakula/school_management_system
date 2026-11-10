document.addEventListener("DOMContentLoaded", function () {

    const sidebar = document.getElementById("sidebar");
    const sidebarToggle = document.getElementById("sidebarToggle");

    console.log("SIDEBAR JS LOADED");

    if (!sidebar) {
        console.error("Sidebar element not found");
        return;
    }

    if (!sidebarToggle) {
        console.error("Sidebar toggle button not found");
        return;
    }


    /* =====================================================
       TOGGLE BUTTON
    ===================================================== */

    sidebarToggle.addEventListener("click", function (event) {

        event.preventDefault();
        event.stopPropagation();

        sidebar.classList.toggle("sidebar-open");

        console.log(
            "Sidebar open:",
            sidebar.classList.contains("sidebar-open")
        );

    });


    /* =====================================================
       RESPONSIVE CHECK
    ===================================================== */

    function checkScreenSize() {

        if (window.innerWidth <= 900) {

            /*
             * Mobile / Tablet
             * Start closed
             */

            sidebar.classList.remove("sidebar-open");

        } else {

            /*
             * Desktop
             * Always open
             */

            sidebar.classList.remove("sidebar-open");

        }

    }


    /* =====================================================
       INITIAL
    ===================================================== */

    checkScreenSize();


    /* =====================================================
       RESIZE
    ===================================================== */

    let previousWidth = window.innerWidth;

    window.addEventListener("resize", function () {

        const currentWidth = window.innerWidth;

        /*
         * Only reset when crossing the 900px breakpoint.
         */

        if (
            (previousWidth > 900 && currentWidth <= 900) ||
            (previousWidth <= 900 && currentWidth > 900)
        ) {

            checkScreenSize();

        }

        previousWidth = currentWidth;

    });

});