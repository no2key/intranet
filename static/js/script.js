/* Author: Junyu Wang (junyu@wandoujia.com)

*/
$("*[rel=popover]").popover({"placement": "left"});
$("*[rel=tooltip]").tooltip();
$("input.type.platform").click(function() {
  if ($(this).attr("checked") == "checked") {
    $("input.due_on").removeAttr("disabled");
    $("select.dependency").attr("disabled", "disabled");
  } else {
    $("input.due_on").attr("disabled", "disabled");
    $("select.dependency").removeAttr("disabled");
  }
});
$("input.type.product").click(function() {
  if ($(this).attr("checked") == "checked") {
    $("input.due_on").attr("disabled", "disabled");
    $("select.dependency").removeAttr("disabled");
  } else {
    $("input.due_on").removeAttr("disabled");
    $("select.dependency").attr("disabled", "disabled");
  }
});
$("form").submit(function() {
  $(this).find('button:submit.btn-primary').button("loading");
});