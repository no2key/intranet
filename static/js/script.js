/* Author: Junyu Wang (junyu@wandoujia.com)

*/
$("*[rel=popover]").popover({"placement": "left"});
$("*[rel=tooltip]").tooltip();
$("input.type.platform").click(function() {
  if ($(this).attr("checked") == "checked") {
    usePlatform();
  } else {
    useProduct();
  }
});
$("input.type.product").click(function() {
  if ($(this).attr("checked") == "checked") {
    useProduct();
  } else {
    usePlatform();
  }
});

$("input.impact").click(function() {
  if ($("input.type.product").attr("checked") == "checked") {
    useProduct();
  }
});

$("form").submit(function() {
  $(this).find('button:submit.btn-primary').button("loading");
});

useProduct = function() {
  $("div.controls-platform *").attr("disabled", "disabled");
  $("div.controls-product input:radio").attr("disabled", "disabled");
  $("input.impact").each(function() {
    if ($(this).attr("checked") == "checked") {
      switch ($(this).val()) {
        case "major":
          $("table.dependency tr.impact-major input:radio").removeAttr("disabled");
          break;
        case "minor":
          $("table.dependency tr.impact-major input:radio").removeAttr("disabled");
          $("table.dependency tr.impact-minor input:radio").removeAttr("disabled");
          break;
        case "beta":
          $("table.dependency tr.impact-major input:radio").removeAttr("disabled");
          $("table.dependency tr.impact-minor input:radio").removeAttr("disabled");
          $("table.dependency tr.impact-beta input:radio").removeAttr("disabled");
          break;
        case "experimental":
          $("table.dependency tr.impact-major input:radio").removeAttr("disabled");
          $("table.dependency tr.impact-minor input:radio").removeAttr("disabled");
          $("table.dependency tr.impact-beta input:radio").removeAttr("disabled");
          $("table.dependency tr.impact-experimental input:radio").removeAttr("disabled");
          break;
        case "dogfood":
          $("table.dependency tr.impact-dogfood input:radio").removeAttr("disabled");
          break;
      }
    }
  });
};

usePlatform = function() {
  $("div.controls-platform *").removeAttr("disabled", "disabled");
  $("div.controls-product").attr("disabled", "disabled");
};