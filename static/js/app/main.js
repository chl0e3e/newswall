define(["jquery", "masonry", "imagesloaded", "site-query-builder", "materialize", "log"], function($, Masonry, imagesLoaded, SiteQueryBuilder, materialize, log) {
    $(function() {
        const socket = new WebSocket("ws://localhost:8080/main");

        function send(data) {
            return socket.send(JSON.stringify(data));
        }

        socket.addEventListener("open", function (event) {
            console.log("Socket open");
            send({"cmd": "sites"});
        });

        var queryBuilder;

        $("#btn-reset").on("click", function() {

        });
        
        $("#btn-query").on("click", function() {
            if(typeof queryBuilder !== "undefined") {
                var query = queryBuilder.query();
                console.log(query);
                console.log(JSON.stringify(query));
                send({
                    "cmd": "query",
                    "data": query
                });
            } else {
                alert("The query builder is not initialised.");
            }
        });
        
        $("#btn-add-as-filter").on("click", function() {

        });

        $("#tab-query").on("click", function() {
            var querySection = $("#query");
            if(querySection.hasClass("hidden")) {
                querySection.slideDown( "fast", function() {
                    querySection.removeClass("hidden");
                });
            } else {
                querySection.slideUp( "fast", function() {
                    querySection.addClass("hidden");
                });
            }
        });

        $("#tab-log").on("click", function() {
            var logSection = $("#log");
            if(logSection.hasClass("hidden")) {
                logSection.slideDown( "fast", function() {
                    logSection.removeClass("hidden");
                });
            } else {
                logSection.slideUp( "fast", function() {
                    logSection.addClass("hidden");
                });
            }
        });

        window.gridElements = [];
        window.currentData = [];
        window.masonry = null;
        window.gridEnabled = true;

        function destroy() {
            if (window.gridEnabled) {
                window.gridElements.forEach(function(el) {
                    window.masonry.remove(el);
                });
                window.masonry.layout();
                window.gridElements = [];
            } else {
                $("#list article").remove();
            }

            window.currentData = [];
        }
        
        function tabAllClick(e) {
            destroy();

            var queryRules = [];

            for (var site in window.sites) {
                queryRules.push({"type":"rule","children":[],"filter":"site","operator":"equals","value":site});
            }

            send({
                "cmd": "query",
                "data": {"type":"root","children":queryRules}
            });
        }
        $("#tab-all").on("click", tabAllClick);

        function tabSiteClick(e) {
            var tabElement = $(e.target).closest(".nav-link");
            var tabSiteID = tabElement.attr("data-site-id");
            $(".queried").removeClass("queried");
            tabElement.addClass("queried");

            destroy();

            send({
                "cmd": "query",
                "data": {"type":"root","children":[{"type":"rule","children":[],"filter":"site","operator":"equals","value":tabSiteID}]}
            });
        }

        function readCurrentData() {
            let gridArticlesLoaded = [];

            for(var reportIndex in window.currentData) {
                let report = window.currentData[reportIndex];
                if (window.gridEnabled) {
                    let articleGridItem = $("<article></article>")
                        .attr("id", "grid_" + report._id)
                        .append($("<a></a>")
                            .attr("href", report.url)
                            .append($("<img />")
                                .attr("src", report.screenshot_url)
                                .attr("alt", "")));

                    articleGridItem.css("display", "none");
                    gridArticlesLoaded.push(articleGridItem[0]);
                    $("#wall").append(articleGridItem);
                } else {
                    let articleListItem = $("<article></article>")
                        .attr("id", "list_" + report._id)
                        .attr("class", "collection-item")
                        .append($("<a></a>")
                            .attr("href", report.url)
                            .append($("<div></div>")
                                .attr("class", "image")
                                .append($("<img />")
                                    .attr("src", report.screenshot_url)
                                    .attr("alt", report.title)))
                            .append($("<div></div>")
                                .attr("class", "info")
                                .append($("<h5></h5>")
                                    .text(report.title))));
                    $("#list").append(articleListItem);
                }
            }

            if (window.gridEnabled) {
                window.imagesLoaded($("#wall")[0], function() {
                    for (var articleGridIndex in gridArticlesLoaded) {
                        let articleGridItem = gridArticlesLoaded[articleGridIndex];
                        masonry.appended(articleGridItem);
                        window.gridElements.push(articleGridItem);
                    }

                    masonry.layout();
                });
            }
        }

        function grid(enabled) {
            if(enabled) {
                $("#btn-change-view").find("i").text("grid_off");
                $("#list").hide();
                $("#wall").show();
                window.masonry = new Masonry("#wall", {
                    itemSelector: "article",
                    columnWidth: 10,
                    horizontalOrder: true
                });
                readCurrentData();
            } else {
                $("#wall").hide();
                if(window.masonry != null) {
                    window.masonry.destroy();
                    window.masonry = null;
                }

                $("#list").show();
                $("#btn-change-view").find("i").text("grid_on");
                readCurrentData();
            }
        }

        grid(window.gridEnabled);

        $("#btn-change-view").on("click", function(e) {
            window.gridEnabled = !window.gridEnabled;
            grid(window.gridEnabled);
        });

        socket.addEventListener("message", function (event) {
            const message = JSON.parse(event.data);

            if (message.cmd == "sites") {
                if(typeof queryBuilder === "undefined") {
                    window.sites = message.data;

                    for(var site in message.data) {
                        var siteData = message.data[site];
                        var tabImage = $("<img />")
                            .attr("alt", siteData["name"])
                            .attr("src", siteData["logo"]);
                        var tabImageContainer = $("<div></div>")
                            .attr("class", "image-container")
                            .append(tabImage);
                        var tabLink = $("<a></a>")
                            .attr("class", "nav-link")
                            .attr("href", "#")
                            .attr("data-site-id", site)
                            .click(tabSiteClick)
                            .append(tabImageContainer);
                        var tab = $("<li></li>")
                            .attr("class", "tab")
                            .append(tabLink);

                        tab.insertAfter($("#tab-log"));
                    }
                    
                    queryBuilder = new SiteQueryBuilder("builder", message.data);
                    $("#builder-container").append(queryBuilder.render());
                    queryBuilder.postRender();
                }
            } else if(message.cmd == "report") {
                window.currentData = message.report;
                readCurrentData();
            } else if(message.cmd == "log") {
                $("#log > table > tbody").append($("<tr></tr>")
                    .append($("<th></th>")
                        .attr("scope", "row")
                        .text(message.log.date))
                    .append($("<td></td>")
                        .text(message.log.source))
                    .append($("<td></td>")
                        .text(message.log.text)))
            }
        });
    });
});