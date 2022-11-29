define(["jquery", "masonry", "imagesloaded"], function($, Masonry, imagesLoaded) {
    $(function() {
        const socket = new WebSocket('ws://localhost:8080/main');

        function send(data) {
            return socket.send(JSON.stringify(data));
        }

        socket.addEventListener('open', function (event) {
            console.log("Socket open");
        });

        const masonry = new Masonry('#wall', {
            itemSelector: 'article',
            columnWidth: 80
        });

        function setFilter(filter) {
            window.filter = filter;
            localStorage.setItem("filter", JSON.stringify(filter));
            sendFilter();
        }

        function sendFilter() {
            send({"cmd": "filter", "filter": window.filter});
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

        function tabLogClick(e) {
            $("#wall").hide();
            $("#log").show();
        }

        $("#tab-all").click(tabAllClick);
        $("#tab-log").click(tabLogClick);

        socket.addEventListener('message', function (event) {
            const parsedData = JSON.parse(event.data);

            if (parsedData.cmd == "sites") {
                window.sites = parsedData.sites;

                for(var site in parsedData.sites) {
                    var tabLink = $('<a></a>')
                        .attr("class", "nav-link")
                        .attr("href", "#")
                        .text(parsedData.sites[site])
                        .click(tabClick);
                    var tab = $('<li></li>')
                        .attr("class", "nav-item")
                        .attr("data-site", site)
                        .append(tabLink);

                    $("#tab-all").insertAfter(tab);
                }

                if (localStorage.getItem("filter") === null) {
                    var filter = {};
                    for(var site in parsedData.sites) {
                        filter[site] = "*";
                    }
                    setFilter(filter);
                } else {
                    window.filter = JSON.parse(localStorage.getItem("filter"));
                }

                sendFilter();
            } else if(parsedData.cmd == "report") {
                let articles = [];
                for(var reportIndex in parsedData.report) {
                    let report = parsedData.report[reportIndex];

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
            } else if(parsedData.cmd == "log") {
                $("#log > table > tbody").append($("<tr></tr>")
                    .append($("<th></th>")
                        .attr("scope", "row")
                        .text(parsedData.log.date))
                    .append($("<td></td>")
                        .text(parsedData.log.source))
                    .append($("<td></td>")
                        .text(parsedData.log.text)))
            }
        });
    });
});