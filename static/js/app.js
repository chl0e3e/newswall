requirejs.config({
    "baseUrl": "static/js/",
    "paths": {
        "jquery": "lib/jquery-3.6.0",
        "bootstrap": "lib/bootstrap.bundle.min",
        "masonry": "lib/masonry.pkgd.min",
        "imagesloaded": "lib/imagesloaded.pkgd.min",
        "app": "app/main"
    }
});

// Load the main app module to start the app
requirejs(["app"]);