requirejs.config({
    "baseUrl": "static/js/",
    "paths": {
        "xterm": "lib/xterm.min",
        "xterm.fit": "lib/xterm.fit.min",
        "jquery": "lib/jquery-3.6.0",
        "materialize": "lib/materialize.min",
        "masonry": "lib/masonry.pkgd.min",
        "imagesloaded": "lib/imagesloaded.pkgd.min",
        "uuidv4": "app/uuidv4",
        "log": "app/log",
        "site-query-builder": "app/site-query-builder",
        "app": "app/main"
    },
    "shim": {
        "xterm.fit": ["xterm"]
    }
});

// Load the main app module to start the app
requirejs(["app"]);