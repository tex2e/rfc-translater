
// ---------------------------------------------------------------------------
// html/rfcXXXX.html

document.addEventListener('DOMContentLoaded', function () {
  const rfc = new RfcUi();
  rfc.dispInit();
});


class RfcUi {
  constructor() {
    this.rfc_draft = null;
  }

  dispInit() {
    // RFCがドラフトかの判定
    this.rfc_draft = this._isDraft();

    // 編集ページの設定
    const footer = this._getFooterHtmlElem();
    if (!this.rfc_draft && footer) {
      this._addEventToShowEditPage();
    }

    // 廃止RFCの表示
    const rfc_alert = this._getAlertHtmlElem();
    if (!this.rfc_draft && rfc_alert) {
      this._showAlertWhenObsoleted();
    }

    // RFCの発行WG（ワーキンググループ）の表示
    const rfc_wg = this._getWgHtmlElem();
    if (!this.rfc_draft && rfc_wg) { // 標準RFC
      this._showWg();
    }
    if (this.rfc_draft && rfc_wg) { // Draft版のRFC
      this._showWgOnDraft();
    }

    // ダークモードへの切り替えボタンの表示
    this._dispDarkmodeButton();

    // 文書内のRFCリンク化
    this._createRfcLink();

    // 文書内の目次リンク化
    this._createTocLink();
  }

  _isDraft() {
    return document.getElementById('rfc_draft');
  }

  _getFooterHtmlElem() {
    return document.getElementById('rfc_footer')
  }

  _addEventToShowEditPage() {
    // 画面を4回連続クリックで編集ページへ移動
    const rfc_number = parseInt(document.getElementById('rfc_number').innerText);
    window.addEventListener('click', function (evt) {
      if (evt.detail === 4) {
        const result = window.confirm("編集ページに移動します");
        if (result) {
          window.location.href = 'edit.html?rfc=' + rfc_number;
        }
      }
    });
  }

  _getAlertHtmlElem() {
    return document.getElementById('rfc_alert');
  }

  _showAlertWhenObsoleted() {
    // 対象RFCが廃止されたか確認し、廃止なら修正版RFCへのリンクを表示する。
    const FETCH_FILENAME = "obsoletes.json";
    const httpRequest = new XMLHttpRequest();
    httpRequest.onreadystatechange = function () {
      if (httpRequest.readyState === XMLHttpRequest.DONE && httpRequest.status === 200) {
        const rfc_number = parseInt(document.getElementById('rfc_number').innerText);
        const data = JSON.parse(httpRequest.responseText);
        const datum = data[rfc_number];
        // console.log(datum);

        // RFCの廃止と修正版の表示
        if (datum && datum["obsoleted_by"]) {
          rfc_alert.classList.remove("hidden");

          const rfc_alert_obsoleted_by = document.getElementById('rfc_alert_obsoleted_by');
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
          const rfc_status = document.getElementById('rfc_status');
          const status = datum['status'];
          // console.log(status);
          const status_color_mapper = {
            // 'Unknown': '',
            'Draft': 'danger', // red
            'Informational': 'warning', // orange
            'Experimental': 'warning', // yellow
            'Best Common Practice': 'danger', // pink
            'Best Current Practice': 'danger', // pink
            'Proposed Standard': 'info', // purple
            'Draft Standard': 'info', // skyblue
            'Internet Standard': 'success', // green
            'Historic': 'secondary', // gray
            // 'Obsolete': '', // brown
          }
          const badge_class = status_color_mapper[status];
          // console.log(badge_class);

          rfc_status.innerHTML = ', ST: <a href="https://www.rfc-editor.org/rfc/rfc2026#section-4.1" class="badge badge-pill badge-' + badge_class + '">' + status + '</a>';
        }
      }
    };
    httpRequest.open('GET', FETCH_FILENAME);
    httpRequest.send();
  }

  _getWgHtmlElem() {
    return document.getElementById('rfc_wg');
  }

  _showWg() {
    // 対象RFCがWorkingGroupによって発行されたRFCの場合、WorkingGroupへのリンクを表示する。
    const FETCH_FILENAME = "group-rfcs.json";
    const httpRequest = new XMLHttpRequest();
    httpRequest.onreadystatechange = function () {
      if (httpRequest.readyState === XMLHttpRequest.DONE && httpRequest.status === 200) {
        const rfc_number = parseInt(document.getElementById('rfc_number').innerText);
        const data = JSON.parse(httpRequest.responseText);
        const wg = data[rfc_number];
        if (wg) {
          const tmp = wg.split('/'); // "wg/tls"
          if (tmp.length >= 2) {
            rfc_wg.innerHTML = ', WG: <a href="https://datatracker.ietf.org/' + wg + '/documents/" class="badge badge-primary">' + tmp[1] + '</a>';
          }
        }
      }
    };
    httpRequest.open('GET', FETCH_FILENAME);
    httpRequest.send();
  }

  _showWgOnDraft() {
    const rfc_draft_name = document.getElementById('rfc_number').innerText;
    const regex = /^draft-[^-]+-(?<wg_name>[^-]+)/;
    const m = regex.exec(rfc_draft_name);
    // console.log(m);
    if (m) {
      const wg = m.groups['wg_name'];
      const tmp = wg.split('/'); // "wg/tls"
      if (tmp.length >= 2) {
        rfc_wg.innerHTML = ', WG: <a href="https://datatracker.ietf.org/' + wg + '/documents/" class="badge badge-primary">' + tmp[1] + '</a>';
      }
    }
  }

  _dispDarkmodeButton() {
    const darkModeHTML = {
      'Light': '<svg viewBox="0 0 24 24" width="24" height="24" class="lightToggleIcon"><path fill="currentColor" d="M12,9c1.65,0,3,1.35,3,3s-1.35,3-3,3s-3-1.35-3-3S10.35,9,12,9 M12,7c-2.76,0-5,2.24-5,5s2.24,5,5,5s5-2.24,5-5 S14.76,7,12,7L12,7z M2,13l2,0c0.55,0,1-0.45,1-1s-0.45-1-1-1l-2,0c-0.55,0-1,0.45-1,1S1.45,13,2,13z M20,13l2,0c0.55,0,1-0.45,1-1 s-0.45-1-1-1l-2,0c-0.55,0-1,0.45-1,1S19.45,13,20,13z M11,2v2c0,0.55,0.45,1,1,1s1-0.45,1-1V2c0-0.55-0.45-1-1-1S11,1.45,11,2z M11,20v2c0,0.55,0.45,1,1,1s1-0.45,1-1v-2c0-0.55-0.45-1-1-1C11.45,19,11,19.45,11,20z M5.99,4.58c-0.39-0.39-1.03-0.39-1.41,0 c-0.39,0.39-0.39,1.03,0,1.41l1.06,1.06c0.39,0.39,1.03,0.39,1.41,0s0.39-1.03,0-1.41L5.99,4.58z M18.36,16.95 c-0.39-0.39-1.03-0.39-1.41,0c-0.39,0.39-0.39,1.03,0,1.41l1.06,1.06c0.39,0.39,1.03,0.39,1.41,0c0.39-0.39,0.39-1.03,0-1.41 L18.36,16.95z M19.42,5.99c0.39-0.39,0.39-1.03,0-1.41c-0.39-0.39-1.03-0.39-1.41,0l-1.06,1.06c-0.39,0.39-0.39,1.03,0,1.41 s1.03,0.39,1.41,0L19.42,5.99z M7.05,18.36c0.39-0.39,0.39-1.03,0-1.41c-0.39-0.39-1.03-0.39-1.41,0l-1.06,1.06 c-0.39,0.39-0.39,1.03,0,1.41s1.03,0.39,1.41,0L7.05,18.36z"></path></svg>',
      'Dark': '<svg viewBox="0 0 24 24" width="24" height="24" class="darkToggleIcon"><path fill="currentColor" d="M9.37,5.51C9.19,6.15,9.1,6.82,9.1,7.5c0,4.08,3.32,7.4,7.4,7.4c0.68,0,1.35-0.09,1.99-0.27C17.45,17.19,14.93,19,12,19 c-3.86,0-7-3.14-7-7C5,9.07,6.81,6.55,9.37,5.51z M12,3c-4.97,0-9,4.03-9,9s4.03,9,9,9s9-4.03,9-9c0-0.46-0.04-0.92-0.1-1.36 c-0.98,1.37-2.58,2.26-4.4,2.26c-2.98,0-5.4-2.42-5.4-5.4c0-1.81,0.89-3.42,2.26-4.4C12.92,3.04,12.46,3,12,3L12,3z"></path></svg>',
    }
    const themeToggleButton = document.createElement('button');
    const navbarText = document.querySelector('#navbarText .navbar-nav:last-child');
    const buttonToOriginal = navbarText.childNodes[0];
    let darkMode = false;
    themeToggleButton.innerHTML = darkModeHTML['Dark'];
    themeToggleButton.classList.add('btn', 'btn-light', 'btn-sm', 'darkModeToggleIcon');
    themeToggleButton.addEventListener('click', function () {
      themeToggleButton.innerHTML = (darkMode) ? darkModeHTML['Dark']: darkModeHTML['Light'];
      darkMode = !darkMode;
      localStorage.setItem('isDarkMode', darkMode.toString());
      document.body.classList.toggle('dark-theme');
    });
    navbarText.insertBefore(themeToggleButton, buttonToOriginal);
    // 前回履歴情報からダークモードの設定
    if (localStorage.getItem('isDarkMode') === 'true') {
      themeToggleButton.click();
    }
  }

  _createRfcLink() {
    const rfc_draft = this.rfc_draft;
    document.querySelectorAll('.row .text').forEach(function (el) {
      // "[RFC5280]" から "<a href="./rfc5280.html">[RFC5280]</a>" へ変換
      // ただし、RFC2220未満は自サイト内に存在しないため、IETFのサイトへのリンクにする
      el.innerHTML = el.innerHTML.replace(/\[RFC([0-9]+)\]/g, function (match, p1) {
        if (parseInt(p1) < 2220) {
          return `<a href="https://datatracker.ietf.org/doc/html/rfc${p1}">[RFC${p1}]</a>`
        } else if (rfc_draft) {
          return `<a href="../rfc${p1}.html">[RFC${p1}]</a>`
        } else {
          return `<a href="./rfc${p1}.html">[RFC${p1}]</a>`
        }
      });
    })
  }

  _createTocLink() {
    // セクション番号とIDの連想配列の作成
    const section_dict = {}
    document.querySelectorAll(".row h5.text[id]").forEach(function (el) {
      // "6-1-6--Outputs" から "6.1.6." を連想配列のキーとして作成
      // "Appendix-C--Examples" から "Appendix C." を連想配列のキーとして作成
      const h5_id_value = el.attributes['id'].value;
      const h5_id_key = h5_id_value.replace(/--+.+$/, '-').replace(/-/g, '.').replace(/^(Appendix)\./, '$1 ');
      section_dict[h5_id_key] = h5_id_value;
    })
    // 目次判定された文章に対してリンクを貼る
    document.querySelectorAll('.row .text.toc').forEach(function (el) {
      // "1.2.3." から "<a href="#1-2-3--Section-Title">1.2.3.</a>" へ変換
      el.innerHTML = el.innerHTML.replace(/(?<= )((?:[A-Z]\.)?(?:\d+\.)+|Appendix [A-Z]\.)(?= )/g, function(match, p1) {
        if (p1 in section_dict) {
          return `<a href="#${section_dict[p1]}">${p1}</a>`
        }
        return p1;
      });
    })
  }

}


// ---------------------------------------------------------------------------
// html/index.html

document.addEventListener('DOMContentLoaded', function () {
  const rfcList = new RfcListUi();
  rfcList.dispInit();
});


class RfcListUi {
  // リストの要素を特定するクエリセレクタ
  static QUERYSELECTOR_RFCLIST_ITEM = "#RFCs.list-group .list-group-item"
  // リストの要素を非表示にするときのCSSクラス
  static CSSCLASS_HIDE = "hidden";

  constructor() {
    this.rfcSearchIndex = {};
  }

  dispInit() {
    this._createIndex();
    // console.log("rfcSearchIndex:", this.rfcSearchIndex);
    const domSearchRfc = document.querySelector('#searchRfc')
    if (domSearchRfc) {
      domSearchRfc.addEventListener('input', () => {
        // 検索文字列が1文字以下のときは、抽出しない
        if (domSearchRfc.value.length <= 1) {
          this._renderRfcListAll();
          return;
        }
        // 検索文字列が2文字以上のときは、タイトルに文字列が含まれるものだけ抽出する
        this._search(domSearchRfc.value);
      });
    }
  }

  _search(searchInput) {
    // console.log("searchText:", searchInput);
    const matchedRfcs = this._searchRfcSet(this._normalizeSearchWord(searchInput));
    this._renderRfcList(matchedRfcs);
  }

  _createIndex() {
    document.querySelectorAll(RfcListUi.QUERYSELECTOR_RFCLIST_ITEM).forEach(el => {
      const rfcId = el.attributes["id"].value;
      const rfcNumber = rfcId.replace(/^RFC/, "");
      const rfcTitle = el.innerText;
      const rfcTitleKeywords = rfcTitle.toLowerCase().split(" ").filter(x => !x.match(/^(?:rfc|-)$/)).map(this._normalizeSearchWord)
      const rfcTitleKeywordSet = new Set(rfcTitleKeywords);
      this.rfcSearchIndex[rfcNumber] = rfcTitleKeywordSet;
    });
  }

  _searchRfcSet(searchInput) {
    const matchedRfcs = [];
    // 検索ワードをスペース区切りで抽出する（ただし空白は除外）
    const searchWords = searchInput.split(" ").filter(x => x.length > 0);
    // 全てのRFCタイトルに対して検索を行う
    Object.keys(this.rfcSearchIndex).forEach(rfcNumber => {
      // 複数の検索ワードの全てを含むRFCタイトルのみ抽出する
      const rfcTitleKeywords = Array.from(this.rfcSearchIndex[rfcNumber]);
      const matched = searchWords.every(searchWord => {
        return rfcTitleKeywords.some(keyword => keyword.startsWith(searchWord));
      })
      if (matched) {
        matchedRfcs.push(rfcNumber);
      }
    });
    // console.log("matchedRfcs:", matchedRfcs);
    return new Set(matchedRfcs);
  }

  _renderRfcList(rfcNumbers) {
    document.querySelectorAll(RfcListUi.QUERYSELECTOR_RFCLIST_ITEM).forEach(el => {
      const rfcId = el.attributes["id"].value;
      const rfcNumber = rfcId.replace(/^RFC/, "");
      if (rfcNumbers.has(rfcNumber)) {
        el.classList.remove(RfcListUi.CSSCLASS_HIDE);
      } else {
        el.classList.add(RfcListUi.CSSCLASS_HIDE);
      }
    });
  }

  _renderRfcListAll() {
    document.querySelectorAll(RfcListUi.QUERYSELECTOR_RFCLIST_ITEM).forEach(el => {
      el.classList.remove(RfcListUi.CSSCLASS_HIDE);
    });
  }

  _normalizeSearchWord(word) {
    return word.replace(/[-()/:]/, '')
  }
}
