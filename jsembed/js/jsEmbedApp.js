define([
  'jquery',
  'underscore',
  'backbone',
  'views/recapView'
], function($, _, Backbone, RecapView){
  var initialize = function(){

      var elements = $('.recap');

      _.each(elements, function(el){
        var newView = new RecapView({
          el: el,
          model: $(el).data('url')
        });
        newView.render();
      });


      $('button').click(function(){
        var newView = new RecapView({
          el: $('.recap'),
          model: $('input').val()
        });
        newView.render();
      })
    }

  return {
    initialize: initialize
  };
});
