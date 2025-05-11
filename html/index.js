
// ---------------------------------------------------------------------------
// html/rfcXXXX.html

document.addEventListener('DOMContentLoaded', function () {
  const rfc = new RfcUi();
  rfc.dispInit();
});


class RfcIndexJsonElem {
  static OBSOLETES = 'obs'
  static OBSOLETED_BY = 'obs_by'
  static UPDATES = 'upd'
  static UPDATED_BY = 'upd_by'
  static CURRENT_STATUS = 'st'
  static WG = 'wg'
}

class RfcUi {
  // RFCのページ表示時に取得する追加情報のファイル名
  static FETCH_FILENAME = "data-rfc-list.json";

  constructor() {
    this.domRfcDraft = null;
  }

  dispInit() {
    // RFCがドラフト版かの判定
    this.domRfcDraft = this._isDraft();

    // 編集ページの設定
    const domFooter = this._getFooterHtmlDomElem();
    if (!this.domRfcDraft && domFooter) {
      this._addEventToShowEditPage();
    }

    // 廃止RFCの表示、WGの表示
    this._fetchDataRfcListJson();

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

  _getFooterHtmlDomElem() {
    return document.getElementById('rfc_footer')
  }

  _addEventToShowEditPage() {
    // 画面を4回連続クリックで編集ページへ移動
    const domRfcNumber = document.getElementById('rfc_number');
    const rfcNumber = parseInt(domRfcNumber.innerText);
    window.addEventListener('click', function (evt) {
      if (evt.detail === 4) {
        const result = window.confirm("編集ページに移動します");
        if (result) {
          window.location.href = `edit.html?rfc=${rfcNumber}`;
        }
      }
    });
  }

  _fetchDataRfcListJson() {
    const httpRequest = new XMLHttpRequest();
    httpRequest.onreadystatechange = () => {
      if (httpRequest.readyState === XMLHttpRequest.DONE && httpRequest.status === 200) {
        const domRfcNumber = document.getElementById('rfc_number');
        if (!domRfcNumber) {
          return;
        }
        const rfcNumber = parseInt(domRfcNumber.innerText);
        const data = JSON.parse(httpRequest.responseText);
        const datum = data[rfcNumber];
        // console.log(datum);

        this._showAlertWhenObsoleted(rfcNumber, datum);
        this._showWg(rfcNumber, datum);
      }
    };
    httpRequest.open('GET', RfcUi.FETCH_FILENAME);
    httpRequest.send();
  }

  _getAlertHtmlDomElem() {
    return document.getElementById('rfc_alert');
  }

  _showAlertWhenObsoleted(_rfcNumber, datum) {
    // 対象RFCが廃止されたか確認し、廃止なら修正版RFCへのリンクを表示する。
    const domRfcAlert = this._getAlertHtmlDomElem();
    if (!this.domRfcDraft && domRfcAlert) {
      // RFCの廃止と修正版の表示
      if (datum && datum[RfcIndexJsonElem.OBSOLETED_BY]) {
        domRfcAlert.classList.remove("hidden");

        const domRfcAlertObsoletedBy = document.getElementById('rfc_alert_obsoleted_by');
        let rfc_links = "";
        if (datum[RfcIndexJsonElem.OBSOLETED_BY].length >= 1) {
          for (let i = 0; i < datum[RfcIndexJsonElem.OBSOLETED_BY].length; i++) {
            let rfcNumber = datum[RfcIndexJsonElem.OBSOLETED_BY][i];
            rfc_links += `<a href="./rfc${rfcNumber}.html">RFC ${rfcNumber}</a>`;
            if (i + 1 < datum[RfcIndexJsonElem.OBSOLETED_BY].length) {
              rfc_links += ", ";
            }
          }
        }
        if (rfc_links !== "") {
          domRfcAlertObsoletedBy.innerHTML = `このRFCは廃止されました。修正版は <span>${rfc_links}</span> です。`;
        }
      }

      // RFCステータスの表示
      if (datum && datum[RfcIndexJsonElem.CURRENT_STATUS]) {
        const domRfcStatus = document.getElementById('rfc_status');
        const status = datum[RfcIndexJsonElem.CURRENT_STATUS];
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

        domRfcStatus.innerHTML = `, ST: <a href="https://www.rfc-editor.org/rfc/rfc2026#section-4.1" class="badge badge-pill badge-${badge_class}">${status}</a>`;
      }
    }
  }

  _getWgHtmlDomElem() {
    return document.getElementById('rfc_wg');
  }

  _showWg(_rfc_number, datum) {
    // 対象RFCがWorkingGroupによって発行されたRFCの場合、WorkingGroupへのリンクを表示する。
    const domRfcWg = this._getWgHtmlDomElem();
    if (!this.domRfcDraft && domRfcWg) {
      const wg = datum[RfcIndexJsonElem.WG];
      if (wg) {
        domRfcWg.innerHTML = `, WG: <a href="https://datatracker.ietf.org/wg/${wg}/documents/" class="badge badge-primary">${wg}</a>`;
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
    document.querySelectorAll('.row .text').forEach(el => {
      // "[RFC5280]" から "<a href="./rfc5280.html">[RFC5280]</a>" へ変換
      // ただし、RFC2220未満は自サイト内に存在しないため、IETFのサイトへのリンクにする
      el.innerHTML = el.innerHTML.replace(/\[RFC([0-9]+)\]/g, (match, p1) => {
        if (parseInt(p1) < 2220) {
          return `<a href="https://datatracker.ietf.org/doc/html/rfc${p1}">[RFC${p1}]</a>`
        } else if (this.domRfcDraft) {
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
  rfcList.setup();
});


class RfcListUi {
  // リストの要素を特定するクエリセレクタ
  static QUERYSELECTOR_RFCLIST_ITEM = "#RFCs.list-group .list-group-item"
  // リストの要素を非表示にするときのCSSクラス
  static CSSCLASS_HIDE = "hidden";

  constructor() {
    this.rfcSearchIndex = {};
  }

  // 初期設定
  setup() {
    this._createIndex();
    // console.log("rfcSearchIndex:", this.rfcSearchIndex);
    const domSearchRfc = document.querySelector('#searchRfc');
    if (domSearchRfc) {
      // RFCタイトル検索項目入力時のイベント登録
      domSearchRfc.addEventListener('input', () => {
        // 検索文字列が1文字以下のときは、抽出しない
        if (domSearchRfc.value.length <= 1) {
          this._renderRfcListAll();
          return;
        }
        // 検索文字列が2文字以上のときは、タイトルに文字列が含まれるものだけ抽出する
        this._search(domSearchRfc.value?.toLowerCase());
      });
    }
  }

  // 検索処理
  _search(searchInput) {
    // console.log("searchText:", searchInput);
    const matchedRfcs = this._searchRfcSet(this._normalizeSearchWord(searchInput));
    this._renderRfcList(matchedRfcs);
  }

  // 検索用インデックスの作成
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

  // インデックスを利用した検索処理
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

  // 指定したRFC一覧の描画
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

  // RFC一覧の描画
  _renderRfcListAll() {
    document.querySelectorAll(RfcListUi.QUERYSELECTOR_RFCLIST_ITEM).forEach(el => {
      el.classList.remove(RfcListUi.CSSCLASS_HIDE);
    });
  }

  // 検索キーワードの静音化
  _normalizeSearchWord(word) {
    return word.replace(/[-()/:]/, '')
  }
}
