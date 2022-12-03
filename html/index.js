
document.addEventListener('DOMContentLoaded', function () {

  // ---------------------------------------------------------------------------
  // rfcXXXX.html
  // ---------------------------------------------------------------------------

  let rfc_draft = document.getElementById('rfc_draft');

  // 編集ページの設定
  let footer = document.getElementById('rfc_footer');
  if (!rfc_draft && footer) {
    // 編集ページ表示方法
    let rfc_number = parseInt(document.getElementById('rfc_number').innerText);
    window.addEventListener('click', function (evt) {
      if (evt.detail === 4) {
        let result = window.confirm("編集ページに移動します");
        if (result) {
          window.location.href = 'edit.html?rfc=' + rfc_number;
        }
      }
    });
  }

  // 廃止RFCの表示
  let rfc_alert = document.getElementById('rfc_alert');
  if (!rfc_draft && rfc_alert) {
    // 対象RFCが廃止されたか確認し、廃止なら修正版RFCへのリンクを表示する。
    let httpRequest = new XMLHttpRequest();
    httpRequest.onreadystatechange = function () {
      if (httpRequest.readyState === XMLHttpRequest.DONE && httpRequest.status === 200) {
        let rfc_number = parseInt(document.getElementById('rfc_number').innerText);
        let data = JSON.parse(httpRequest.responseText);
        let datum = data[rfc_number];
        // console.log(datum);

        // RFCの廃止と修正版の表示
        if (datum && datum["obsoleted_by"]) {
          rfc_alert.classList.remove("hidden");

          let rfc_alert_obsoleted_by = document.getElementById('rfc_alert_obsoleted_by');
          let rfc_links = "";
          if (datum["obsoleted_by"].length >= 1) {
            for (let i = 0; i < datum["obsoleted_by"].length; i++) {
              let rfc_number = datum["obsoleted_by"][i];
              rfc_links += '<a href="./rfc' + rfc_number + '.html">RFC ' + rfc_number + '</a>';
              if (i + 1 < datum["obsoleted_by"].length) {
                rfc_links += ", ";
              }
            }
          }
          if (rfc_links !== "") {
            rfc_alert_obsoleted_by.innerHTML = "このRFCは廃止されました。修正版は <span>" + rfc_links + "</span> です。";
          }
        }

        // RFCステータスの表示
        if (datum && datum['status']) {
          let rfc_status = document.getElementById('rfc_status');
          let status = datum['status'];
          // console.log(status);
          let status_color_mapper = {
            // 'Unknown': '',
            'Draft': 'danger', // red
            'Informational': 'warning', // orange
            'Experimental': 'warning', // yellow
            'Best Common Practice': 'danger', // pink
            'Proposed Standard': 'info', // purple
            'Draft Standard': 'info', // skyblue
            'Internet Standard': 'success', // green
            'Historic': 'secondary', // gray
            // 'Obsolete': '', // brown
          }
          let badge_class = status_color_mapper[status];
          // console.log(badge_class);

          rfc_status.innerHTML = ', ST: <a href="https://www.rfc-editor.org/rfc/rfc2026#section-4.1" class="badge badge-pill badge-' + badge_class + '">' + status + '</a>';
        }
      }
    };
    httpRequest.open('GET', 'obsoletes.json');
    httpRequest.send();
  }

  // RFCの発行WG（ワーキンググループ）の表示
  let rfc_wg = document.getElementById('rfc_wg');
  if (!rfc_draft && rfc_wg) { // 標準RFC
    // 対象RFCがWorkingGroupによって発行されたRFCの場合、WorkingGroupへのリンクを表示する。
    let httpRequest = new XMLHttpRequest();
    httpRequest.onreadystatechange = function () {
      if (httpRequest.readyState === XMLHttpRequest.DONE && httpRequest.status === 200) {
        let rfc_number = parseInt(document.getElementById('rfc_number').innerText);
        let data = JSON.parse(httpRequest.responseText);
        let wg = data[rfc_number];
        if (wg) {
          let tmp = wg.split('/'); // "wg/tls"
          if (tmp.length >= 2) {
            rfc_wg.innerHTML = ', WG: <a href="https://datatracker.ietf.org/' + wg + '/documents/" class="badge badge-primary">' + tmp[1] + '</a>';
          }
        }
      }
    };
    httpRequest.open('GET', 'group-rfcs.json');
    httpRequest.send();
  }
  if (rfc_draft && rfc_wg) { // Draft版のRFC
    let rfc_draft_name = document.getElementById('rfc_number').innerText;
    let regex = /^draft-[^-]+-(?<wg_name>[^-]+)/;
    let m = regex.exec(rfc_draft_name);
    // console.log(m);
    if (m) {
      let wg = m.groups['wg_name'];
      let tmp = wg.split('/'); // "wg/tls"
      if (tmp.length >= 2) {
        rfc_wg.innerHTML = ', WG: <a href="https://datatracker.ietf.org/' + wg + '/documents/" class="badge badge-primary">' + tmp[1] + '</a>';
      }
    }
  }

  // ダークモードへの切り替えボタンの表示
  const themeToggleButton = document.createElement('button');
  const buttonToOriginalContainer = document.getElementsByClassName('jump-to-original-rfc-container')[0];
  const buttonToOriginal = buttonToOriginalContainer.childNodes[0];
  let darkMode = false;
  themeToggleButton.innerText = 'Dark';
  themeToggleButton.classList.add('btn', 'btn-light', 'btn-sm');
  themeToggleButton.addEventListener('click', function () {
    themeToggleButton.innerText = (darkMode) ? 'Dark': 'Light';
    darkMode = !darkMode;
    document.body.classList.toggle('dark-theme');
  });
  buttonToOriginalContainer.insertBefore(themeToggleButton, buttonToOriginal);

  // 文書内のRFCリンク化
  document.querySelectorAll('.row .text').forEach(function (el) {
    // "[RFC5280]" から "<a href="./rfc5280.html">[RFC5280]</a>" へ変換
    // ただし、RFC2220未満は自サイト内に存在しないため変換なし
    el.innerHTML = el.innerHTML.replace(/\[RFC([0-9]+)\]/g, function (match, p1) {
      if (parseInt(p1) < 2220) {
        return "[RFC" + p1 + "]"
      }
      return '<a href="./rfc' + p1 + '.html">[RFC' + p1 + ']</a>'
    });
  })

  // 文書内の目次リンク化
  //   セクション番号とIDの連想配列の作成
  let section_dict = {}
  document.querySelectorAll(".row h5.text[id]").forEach(function (el) {
    // "6-1-6--Outputs" から "6.1.6." を連想配列のキーとして作成
    // "Appendix-C--Examples" から "Appendix C." を連想配列のキーとして作成
    const h5_id_value = el.attributes['id'].value;
    const h5_id_key = h5_id_value.replace(/--+.+$/, '-').replace(/-/g, '.').replace(/^(Appendix)\./, '$1 ');
    section_dict[h5_id_key] = h5_id_value;
  })
  //   目次判定された文章に対してリンクを貼る
  document.querySelectorAll('.row .text.toc').forEach(function (el) {
    // "1.2.3." から "<a href="#1-2-3--Section-Title">1.2.3.</a>" へ変換
    el.innerHTML = el.innerHTML.replace(/(?<= )((?:[A-Z]\.)?(?:\d+\.)+|Appendix [A-Z]\.)(?= )/g, function(match, p1) {
      if (p1 in section_dict) {
        return '<a href="#' + section_dict[p1] + '">' + p1 + '</a>';
      }
      return p1;
    });
  })
});
