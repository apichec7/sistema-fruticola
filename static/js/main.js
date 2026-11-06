
document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    const toggle = document.getElementById("menuToggle");

    if (!sidebar || !overlay || !toggle) return;

    function cerrarMenu() {
        sidebar.classList.remove("show");
        overlay.classList.remove("show");
        toggle.setAttribute("aria-expanded", "false");
    }

    toggle.addEventListener("click", function () {
        const abierto = sidebar.classList.toggle("show");
        overlay.classList.toggle("show", abierto);
        toggle.setAttribute("aria-expanded", String(abierto));
    });

    overlay.addEventListener("click", cerrarMenu);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") cerrarMenu();
    });

    sidebar.querySelectorAll("a").forEach(function (enlace) {
        enlace.addEventListener("click", cerrarMenu);
    });
});
