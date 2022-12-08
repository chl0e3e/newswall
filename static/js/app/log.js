define(["jquery", "xterm", "xterm.fit"], function($, xterm, XTERM_FIT) {
    var term = null;
    window.term = xterm;
    $(function() {
        term = new xterm.Terminal({
            //fontFamily: '"Cascadia Code", Menlo, monospace',
            //theme: baseTheme,
            cursorBlink: true,
            //cols: 200,
            //rows: 5000
        });
        term.open($("#log-container")[0]);
    });
    return function(line) {
        term.writeln(line);
    }
});