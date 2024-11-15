window.addEventListener('load', () =>{
    console.log("Window Ready...");
});

setTimeout(() => {
    console.log("Reload");
    location.reload();
}, 10000);