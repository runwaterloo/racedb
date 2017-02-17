define(['jquery', 'underscore', 'backbone', 'jinja', 'text!templates/recapView.html'],
  function($, _, Backbone, jinja, template) {

  var RecapView = Backbone.View.extend({
    initialize: function() {
    //  this.template = _.template(template);
      this.template = jinja.compile(template).render;

    },
    render: function() {
      var self = this;

      var fullUrl = "http://results.runwaterloo.com/" + this.model + "?format=json&callback=?";
console.log(fullUrl);
      $.ajax({
        method : 'GET',
      	url: fullUrl,
        dataType: 'json'
      }).success(function(data){
      	var rendered = self.template(data);
console.table(data);
      	$(self.el).html(rendered);
      });

    }


  });



  return  RecapView;
});
