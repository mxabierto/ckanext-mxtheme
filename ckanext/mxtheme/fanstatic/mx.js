$(document).ready(function(){
    $.ajax("https://api.datos.gob.mx/v1/resources?pageSize=1")
    .done(function(data){
      $('.counter-datos-ds').html(data.pagination.total.toLocaleString());
    })
    .fail(function(err){
      console.log('count error', err);
    });
  });
