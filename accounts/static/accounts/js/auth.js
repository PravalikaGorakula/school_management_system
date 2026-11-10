/* =========================================================
   SCHOOL MANAGEMENT SYSTEM
   AUTHENTICATION JAVASCRIPT
========================================================= */


/* =========================================================
   PASSWORD SHOW / HIDE
========================================================= */

function togglePassword(inputId, buttonId) {

    const passwordInput =
        document.getElementById(inputId);

    const toggleButton =
        document.getElementById(buttonId);


    if (!passwordInput || !toggleButton) {
        return;
    }


    if (passwordInput.type === "password") {

        passwordInput.type = "text";

        toggleButton.textContent = "Hide";

        toggleButton.setAttribute(
            "aria-label",
            "Hide password"
        );

    } else {

        passwordInput.type = "password";

        toggleButton.textContent = "Show";

        toggleButton.setAttribute(
            "aria-label",
            "Show password"
        );

    }

}


/* =========================================================
   PASSWORD MATCH CHECK
========================================================= */

function checkPasswordMatch(
    passwordId,
    confirmPasswordId,
    messageId
) {

    const password =
        document.getElementById(passwordId);

    const confirmPassword =
        document.getElementById(confirmPasswordId);

    const message =
        document.getElementById(messageId);


    if (!password || !confirmPassword || !message) {
        return;
    }


    if (
        confirmPassword.value.length > 0 &&
        password.value !== confirmPassword.value
    ) {

        message.textContent =
            "Passwords do not match.";

        message.style.display = "block";

    } else {

        message.textContent = "";

        message.style.display = "none";

    }

}


/* =========================================================
   NEW PASSWORD PAGE
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const password =
            document.getElementById(
                "id_new_password1"
            );

        const confirmPassword =
            document.getElementById(
                "id_new_password2"
            );

        const matchMessage =
            document.getElementById(
                "password-match-message"
            );


        if (
            password &&
            confirmPassword &&
            matchMessage
        ) {

            confirmPassword.addEventListener(
                "input",
                function () {

                    checkPasswordMatch(
                        "id_new_password1",
                        "id_new_password2",
                        "password-match-message"
                    );

                }
            );


            password.addEventListener(
                "input",
                function () {

                    if (
                        confirmPassword.value.length > 0
                    ) {

                        checkPasswordMatch(
                            "id_new_password1",
                            "id_new_password2",
                            "password-match-message"
                        );

                    }

                }
            );

        }

    }
);