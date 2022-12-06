define(["jquery", "xterm", "xterm.fit"], function($, Terminal, xtermFit) {
    var term = new Terminal({
        fontFamily: '"Cascadia Code", Menlo, monospace',
        //theme: baseTheme,
        cursorBlink: true,
        cols: 200,
        rows: 30
    });
    
    term.open($("#log-container")[0]);
    term.writeln("Log component initialised");
    return function(line) {
        term.writeln(line);
    }
});