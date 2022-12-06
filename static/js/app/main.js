define(["jquery", "masonry", "imagesloaded", "site-query-builder", "materialize", "log"], function($, Masonry, imagesLoaded, SiteQueryBuilder, materialize, log) {
    $(function() {
        const socket = new WebSocket("ws://localhost:8080/main");

        const masonry = new Masonry("#wall", {
            itemSelector: "article",
            columnWidth: 80
        });

        function send(data) {
            return socket.send(JSON.stringify(data));
        }

        function setFilter(filter) {
            window.filter = filter;
            localStorage.setItem("filter", JSON.stringify(filter));
            sendFilter();
        }

        function sendFilter() {
            send({"cmd": "filter", "filter": window.filter});
        }

        function requestSites() {
            send({"cmd": "sites"});
        }

        function tabClick(e) {
            $("#wall").show();
            $("#log").hide();

            let tab = $(e.target).parent();
            let site = tab.attr("data-site");
            $("#tabs .active").removeClass("active");
            tab.addClass("active");

            var filter = {};
            filter[site] = "*";
            setFilter(filter);
        }

        function tabAllClick(e) {
            $("#wall").show();
            $("#log").hide();
        }

        $("#tab-all").click(tabAllClick);
        $(".tabs").tabs();
        $('select').formSelect({
            constrainWidth: false
        });

        socket.addEventListener("open", function (event) {
            console.log("Socket open");
            requestSites();
        });

        var queryBuilder;

        $("#btn-reset").on("click", function() {

        });
        
        $("#btn-query").on("click", function() {
            if(typeof queryBuilder !== 'undefined') {
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

        socket.addEventListener("message", function (event) {
            const message = JSON.parse(event.data);

            if (message.cmd == "sites") {
                if(typeof queryBuilder === 'undefined') {
                    queryBuilder = new SiteQueryBuilder("builder", message.data);
                    $("#builder-container").append(queryBuilder.render());
                    queryBuilder.postRender();
                }
                // let optgroups = {
                //     "all_sites": "All Sites",
                // };
                // let filters = [];
                // let siteFilterValues = {};

                // for (const site in message.data) {
                //     optgroups[site] = "--- " + message.data[site]["name"];
                //     siteFilterValues[site] = message.data[site]["name"];
                //     console.log(site);
                // }
                
                // filters.push({
                //     id: "site",
                //     label: "Site",
                //     type: "string",
                //     input: "select",
                //     values: siteFilterValues,
                //     optgroup: "all_sites",
                //     operators: ["equal", "not_equal"]
                // });

                // for (const site in message.data) {
                //     for (const key in message.data[site]["keys"]) {
                //         if (key.startsWith("screenshot_")) {
                //             continue;
                //         }

                //         filters.push({
                //             id: site + "|" + key,
                //             label: message.data[site]["keys"][key],
                //             type: "string",
                //             input: "text",
                //             values: siteFilterValues,
                //             optgroup: site,
                //             operators: ["equal", "not_equal", "begins_with", "not_begins_with", "contains", "not_contains", "ends_with", "not_ends_with", "is_empty", "is_not_empty", "is_null", "is_not_null"]
                //         });
                //     }
                // }

                //console.log(optgroups);
                //console.log(filters);
                
                /*$("#builder").queryBuilder({
                    filters: filters,
                    optgroups: optgroups,
                    //rules: rules_basic
                });*/
                // window.sites = message.sites;

                // for(var site in message.sites) {
                //     var tabLink = $("<a></a>")
                //         .attr("class", "nav-link")
                //         .attr("href", "#")
                //         .text(message.sites[site])
                //         .click(tabClick);
                //     var tab = $("<li></li>")
                //         .attr("class", "nav-item")
                //         .attr("data-site", site)
                //         .append(tabLink);

                //     $("#tab-all").insertAfter(tab);
                // }

                // if (localStorage.getItem("filter") === null) {
                //     var filter = {};
                //     for(var site in message.sites) {
                //         filter[site] = "*";
                //     }
                //     setFilter(filter);
                // } else {
                //     window.filter = JSON.parse(localStorage.getItem("filter"));
                // }

                // sendFilter();
            } else if(message.cmd == "report") {
                let articles = [];
                for(var reportIndex in message.report) {
                    let report = message.report[reportIndex];

                    let article = $("<article></article>")
                        .attr("id", report._id)
                        .append($("<a></a>")
                            .attr("href", report.url)
                            .append($("<img />")
                                .attr("src", report.screenshot_url)
                                .attr("alt", "")));

                    $("#wall").append(article);
                    articles.push(article);
                    //masonry.appended(article);
                }

                window.imagesLoaded($("#wall")[0], function() {
                    for (var articleIndex in articles) {
                        let article = articles[articleIndex];
                        masonry.appended(article);
                    }

                    masonry.layout();
                });
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