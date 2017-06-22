require.config({
  paths: {
    jquery: '../libs/jquery/jquery-min',
    jqueryUi: '../libs/jquery/jquery-ui.min',
    underscore: '../libs/underscore/underscore-min',
    backbone: '../libs/backbone/backbone-optamd3-min',
    text: '../libs/require/text',
    templates: '../templates',
    bootstrap: '../libs/bootstrap/bootstrap.min',
    jinja : '../libs/jinja-js/lib/jinja'
  }
});

require([

  'jsEmbedApp'
], function(App, $){
  App.initialize();


});
