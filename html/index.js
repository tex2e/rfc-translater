
// console.log('hello!');

document.addEventListener('DOMContentLoaded', function () {

  // ---------------------------------------------------------------------------
  // rfcXXXX.html
  // ---------------------------------------------------------------------------

  var footer = document.getElementById('rfc_footer');
  if (footer) {
    // 編集ページ表示方法
    var rfc_number = parseInt(document.getElementById('rfc_number').innerText);
    window.addEventListener('click', function (evt) {
      if (evt.detail === 4) {
        var result = window.confirm("編集ページに移動します");
        if (result) {
          window.location.href = 'edit.html?rfc=' + rfc_number;
        }
      }
    });
  }

  var rfc_alert = document.getElementById('rfc_alert');
  if (rfc_alert) {
    // 対象RFCが廃止されたか確認し、廃止済みなら最新版RFCの場所を表示する。
    var httpRequest = new XMLHttpRequest();
    httpRequest.onreadystatechange = function () {
      if (httpRequest.readyState === XMLHttpRequest.DONE && httpRequest.status === 200) {
        var rfc_number = parseInt(document.getElementById('rfc_number').innerText);
        var data = JSON.parse(httpRequest.responseText);
        var datum = data[rfc_number];
        // console.log(datum);
        if (datum && datum["obsoleted_by"]) {
          rfc_alert.classList.remove("hidden");

          var rfc_alert_obsoleted_by = document.getElementById('rfc_alert_obsoleted_by');
          var rfc_links = "";
          if (datum["obsoleted_by"].length >= 1) {
            var rfc_number = datum["obsoleted_by"][0];
            rfc_links += '<a href="./rfc' + rfc_number + '.html">RFC ' + rfc_number + '</a>';
          }
          rfc_alert_obsoleted_by.innerHTML = rfc_links;
        }
      }
    };
    httpRequest.open('GET', 'obsoletes.json');
    httpRequest.send();
  }

});
