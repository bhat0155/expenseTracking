// main.js — students will add JavaScript here as features are built

document.addEventListener("DOMContentLoaded", () => {
    const trigger = document.getElementById("how-it-works-btn");
    const overlay = document.getElementById("how-it-works-overlay");
    const closeBtn = document.getElementById("how-it-works-close");
    const video = document.getElementById("how-it-works-video");

    if (!trigger || !overlay || !closeBtn || !video) return;

    const openModal = (event) => {
        event.preventDefault();
        video.src = video.dataset.src + "?autoplay=1";
        overlay.hidden = false;
    };

    const closeModal = () => {
        overlay.hidden = true;
        video.src = "";
    };

    trigger.addEventListener("click", openModal);
    closeBtn.addEventListener("click", closeModal);

    overlay.addEventListener("click", (event) => {
        if (event.target === overlay) closeModal();
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !overlay.hidden) closeModal();
    });
});
