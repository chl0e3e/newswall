define(["jquery", "masonry", "imagesloaded", "site-query-builder", "materialize", "log"], function($, Masonry, imagesLoaded, SiteQueryBuilder, materialize, log) {
    $(function() {
        window.gridElements = [];
        window.currentData = [];
        window.masonry = null;
        window.gridEnabled = true;
        window.currentQuery = null;
        window.filters = localStorage.getItem('filters');

        if (localStorage.getItem("filters") === null) {
            window.filters = {};
        } else {
            window.filters = JSON.parse(window.filters);
        }

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
            queryBuilder.reset();
        });
        
        $("#btn-query").on("click", function() {
            if(typeof queryBuilder !== "undefined") {
                destroy();
                var queryResult = queryBuilder.query();
                query(queryResult);
            } else {
                alert("The query builder is not initialised.");
            }
        });

        function addFilter(name) {
            var tabLink = $("<a></a>")
                .attr("class", "nav-link")
                .attr("href", "#")
                .click(function () {
                    destroy();

                    $(".queried").removeClass("queried");
                    $(this).addClass("queried");

                    query(window.filters[name]);
                })
                .text(name)
                .on('contextmenu', function(e) {
                    e.preventDefault();
                    var querySection = $("#query");
                    if(querySection.hasClass("hidden")) {
                        querySection.slideDown( "fast", function() {
                            querySection.removeClass("hidden");
                        });
                    }
                    queryBuilder.load(window.filters[name]);
                    $("#filter_name").val(name);
                });
            var tab = $("<li></li>")
                .attr("class", "tab")
                .append(tabLink);
            tab.insertAfter($("#tab-all"));
            return tab;
        }

        for(var key in window.filters) {
            addFilter(key);
        }
        
        $("#btn-add-as-filter").on("click", function() {
            var filterName = $("#filter_name").val();
            var queryResult = queryBuilder.query();
            var filterExists = filterName in window.filters;
            window.filters[filterName] = queryResult;
            if (!filterExists) {
                addFilter(filterName);
            }
            localStorage.setItem("filters", JSON.stringify(window.filters));
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

        function query(data, pagination={}) {
            window.currentQuery = data;
            console.log(data);

            send({
                "cmd": "query",
                "data": data,
                "pagination": pagination
            });
        }

        window.addEventListener('scroll', function(e) {
            var body = document.body, html = document.documentElement;

            var top = (window.pageYOffset || html.scrollTop)  - (html.clientTop || 0); // https://stackoverflow.com/a/3464890

            var height = Math.max( body.scrollHeight, body.offsetHeight, 
                html.clientHeight, html.scrollHeight, html.offsetHeight ); // https://stackoverflow.com/a/1147768

            if (top + document.body.clientHeight >= height) {
                if(window.currentQuery != null) {
                    var lastReport = window.currentData[window.currentData.length - 1];
                    query(window.currentQuery, {
                        "from": lastReport._id
                    });
                }
            }
        });

        function destroy() {
            if (window.gridEnabled) {
                if(window.masonry != null) {
                    let temp = window.gridElements;
                    window.gridElements = [];
                    temp.forEach(function(el) {
                        window.masonry.remove(el);
                    });
                    window.masonry.layout();
                }
            } else {
                $("#list article").remove();
            }

            window.currentData = [];
        }
        
        function tabAllClick(e) {
            destroy();

            $(".queried").removeClass("queried");
            $(this).find(".nav-link").addClass("queried");

            var queryRules = [];

            for (var site in window.sites) {
                queryRules.push({"type":"rule","children":[],"filter":"site","operator":"equals","value":site});
            }

            query({"type":"root","children":queryRules});
        }
        $("#tab-all").on("click", tabAllClick);

        function tabSiteClick(e) {
            destroy();

            var tabElement = $(e.target).closest(".nav-link");
            var tabSiteID = tabElement.attr("data-site-id");
            $(".queried").removeClass("queried");
            tabElement.addClass("queried");

            query({"type":"root","children":[{"type":"rule","children":[],"filter":"site","operator":"equals","value":tabSiteID}]});
        }

        function readCurrentData() {
            let gridArticlesLoaded = [];

            for(var reportIndex in window.currentData) {
                let report = window.currentData[reportIndex];
                console.log(report);
                if (window.gridEnabled) {
                    if(document.getElementById("grid_" + report._id) != null && window.gridElements.length > 0) {
                        continue;
                    }

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
                    if($("#list_" + report._id).length > 0) {
                        continue;
                    }

                    const detailsFilters = [
                        "summary",
                        "excerpt",
                        "description",
                        "body"
                    ];

                    let articleListItemInfo = $("<div></div>")
                        .attr("class", "info")
                        .append($("<h5></h5>")
                            .text(report.title))
                        .append($("<time></time>")
                            .attr("datetime", report.report_date)
                            .text(report.report_date));
                    
                    for(var detailFilterKey in detailsFilters) {
                        let detailFilter = detailsFilters[detailFilterKey];
                        if (detailFilter in report) {
                            let detail = $("<p></p>")
                                .text(report[detailFilter]);
                            articleListItemInfo.append(detail);
                            break;
                        }
                    }

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
                            .append(articleListItemInfo));
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
                console.log("report");
                console.log(message.data);
                window.currentData = window.currentData.concat(message.data);
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