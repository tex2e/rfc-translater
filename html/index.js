
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

class RfcSummaryJsonElem {
  static SUMMARY = 'summary'
}

// RFCステータスに対応するBootstrapのバッジ色
const RFC_STATUS_BADGE_CLASS = {
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
};

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

        // RFCの変遷グラフ表示ボタンの設定
        if (!this.domRfcDraft) {
          new RfcHistoryGraphUi(rfcNumber, data).setup();
        }
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
        const badge_class = RFC_STATUS_BADGE_CLASS[status];
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
// html/rfcXXXX.html : RFCの変遷グラフ

class RfcHistoryGraphUi {
  // 全RFCの日本語タイトルを格納したファイル名（概要パネルの初回表示時に取得する）
  static FETCH_TITLE_FILENAME = 'data-rfc-title.json';
  // 描画する最大ノード数（念のための上限。現在RFCから関係の近い順に採用する）
  static MAX_NODES = 250;
  // ノードの大きさ・間隔
  static NODE_W = 96;
  static NODE_H = 34;
  static H_GAP = 28;
  static V_GAP = 72;
  static MARGIN = 48;
  // ズームの範囲
  static SCALE_MIN = 0.2;
  static SCALE_MAX = 2.5;

  static SVG_NS = 'http://www.w3.org/2000/svg';

  constructor(rfcNumber, data) {
    this.rfcNumber = String(rfcNumber);
    this.data = data;
    this.dialog = null;
    this.panGroup = null;
    this.view = { tx: 0, ty: 0, scale: 1 };
    this.layoutResult = null;
    // 概要パネル用の取得済みデータ（同じRFCを何度も取得しないように保持する）
    this.titles = null;
    this.summaries = new Map();
    this.detailRfcNumber = null;
  }

  setup() {
    const datum = this.data[this.rfcNumber];
    if (!datum) {
      return;
    }
    // 廃止・更新の関係を1つも持たないRFCではボタンを表示しない
    const relationKeys = [
      RfcIndexJsonElem.OBSOLETES, RfcIndexJsonElem.OBSOLETED_BY,
      RfcIndexJsonElem.UPDATES, RfcIndexJsonElem.UPDATED_BY,
    ];
    const hasRelation = relationKeys.some(key => (datum[key] || []).length > 0);
    if (!hasRelation) {
      return;
    }
    this._addShowGraphButton();
  }

  // 「Orig」ボタンの下に「変遷」ボタンを追加する
  _addShowGraphButton() {
    const container = document.querySelector('.jump-to-original-rfc-container');
    if (!container) {
      return;
    }
    const button = document.createElement('button');
    button.type = 'button';
    button.classList.add('btn', 'btn-light', 'btn-sm', 'rfc-history-open');
    button.title = 'このRFCの変遷をグラフで表示';
    button.innerHTML = '<span class="jump-to-original-rfc">変遷</span>';
    button.addEventListener('click', () => this._openDialog());
    container.appendChild(button);
  }

  _openDialog() {
    if (!this.dialog) {
      this._createDialog();
    }
    this.dialog.showModal();
    this._hideDetail();
    this._resetView();
  }

  _createDialog() {
    const dialog = document.createElement('dialog');
    dialog.classList.add('rfc-history-dialog');

    // タイトルバー（凡例と閉じるボタン）
    const titlebar = document.createElement('div');
    titlebar.classList.add('rfc-history-titlebar');
    titlebar.innerHTML = `
      <strong>RFC ${this.rfcNumber} の変遷</strong>
      <span class="rfc-history-legend">
        <svg width="30" height="10" viewBox="0 0 30 10"><line x1="0" y1="5" x2="26" y2="5" stroke="#d9534f" stroke-width="1.5"></line><path d="M 30 5 L 22 1 L 22 9 z" fill="#d9534f"></path></svg>廃止
        <svg width="30" height="10" viewBox="0 0 30 10"><line x1="0" y1="5" x2="26" y2="5" stroke="#4a89dc" stroke-width="1.5" stroke-dasharray="4 3"></line><path d="M 30 5 L 22 1 L 22 9 z" fill="#4a89dc"></path></svg>更新
        <span class="rfc-history-legend-note">（ドラッグで移動・ホイールで拡大縮小）</span>
      </span>
      <button type="button" class="rfc-history-close" title="閉じる">&times;</button>
    `;
    dialog.appendChild(titlebar);

    // グラフ描画領域
    const canvas = document.createElement('div');
    canvas.classList.add('rfc-history-canvas');
    dialog.appendChild(canvas);

    // グラフの計算と描画
    const { nodes, edges, truncated } = this._buildGraph();
    this.layoutResult = this._computeLayout(nodes, edges);
    canvas.appendChild(this._renderSvg(this.layoutResult, edges));

    // ノードをクリックしたときに表示する概要パネル。
    // パネル内の操作でグラフが移動・拡大縮小しないように、イベントの伝播を止める
    this.detailPanel = document.createElement('div');
    this.detailPanel.classList.add('rfc-history-detail', 'hidden');
    this.detailPanel.addEventListener('pointerdown', (evt) => {
      this.suppressClick = false;  // 直前のドラッグ操作でパネル内のクリックを無視しない
      evt.stopPropagation();
    });
    this.detailPanel.addEventListener('wheel', (evt) => evt.stopPropagation());
    canvas.appendChild(this.detailPanel);

    if (truncated) {
      const note = document.createElement('div');
      note.classList.add('rfc-history-truncated');
      note.innerText = '※ 関係するRFCが多いため、現在のRFCと関係の近いものだけ表示しています。';
      dialog.appendChild(note);
    }

    // 閉じる操作（×ボタン、背景クリック。Escは<dialog>標準機能）
    titlebar.querySelector('.rfc-history-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', (evt) => {
      if (evt.target === dialog) {
        // ドラッグ操作の終了直後は閉じない
        if (this.suppressClick) {
          this.suppressClick = false;
          return;
        }
        dialog.close();
      }
    });

    this._setupPanZoom(canvas);

    document.body.appendChild(dialog);
    this.dialog = dialog;
    this.canvas = canvas;
  }

  // 現在のRFCの系譜だけをBFSで集める。
  // 過去方向（このRFCが廃止・更新してきたRFC）と未来方向（このRFCを廃止・更新したRFC）を
  // それぞれ辿り、直接の系譜に関係しないRFCは表示しない
  _buildGraph() {
    const pastKeys = [RfcIndexJsonElem.OBSOLETES, RfcIndexJsonElem.UPDATES];
    const futureKeys = [RfcIndexJsonElem.OBSOLETED_BY, RfcIndexJsonElem.UPDATED_BY];
    const visited = new Set([this.rfcNumber]);
    let truncated = false;
    for (const relationKeys of [pastKeys, futureKeys]) {
      const queue = [this.rfcNumber];
      while (queue.length > 0) {
        const node = queue.shift();
        const datum = this.data[node] || {};
        for (const key of relationKeys) {
          for (const neighbor of (datum[key] || [])) {
            if (visited.has(neighbor)) {
              continue;
            }
            if (visited.size >= RfcHistoryGraphUi.MAX_NODES) {
              truncated = true;
              continue;
            }
            visited.add(neighbor);
            queue.push(neighbor);
          }
        }
      }
    }

    // 辺の構築（古いRFC → 新しいRFCの向き。両方向に記録されている関係は重複排除する）
    const edgeMap = new Map();
    const addEdge = (src, dst, type) => {
      if (!visited.has(src) || !visited.has(dst)) {
        return;
      }
      edgeMap.set(`${src}>${dst}:${type}`, { src: src, dst: dst, type: type });
    };
    for (const node of visited) {
      const datum = this.data[node] || {};
      for (const m of (datum[RfcIndexJsonElem.OBSOLETES] || [])) addEdge(m, node, 'obs');
      for (const m of (datum[RfcIndexJsonElem.OBSOLETED_BY] || [])) addEdge(node, m, 'obs');
      for (const m of (datum[RfcIndexJsonElem.UPDATES] || [])) addEdge(m, node, 'upd');
      for (const m of (datum[RfcIndexJsonElem.UPDATED_BY] || [])) addEdge(node, m, 'upd');
    }
    return {
      nodes: Array.from(visited),
      edges: Array.from(edgeMap.values()),
      truncated: truncated,
    };
  }

  // 階層レイアウトの計算。RFC番号の昇順（=時系列）に処理し、
  // 先行RFC（このRFCが廃止・更新した相手）の最大階層+1を自身の階層とする
  _computeLayout(nodes, edges) {
    const sortedNodes = nodes.slice().sort((a, b) => parseInt(a) - parseInt(b));
    const preds = new Map();
    for (const edge of edges) {
      if (!preds.has(edge.dst)) {
        preds.set(edge.dst, []);
      }
      preds.get(edge.dst).push(edge.src);
    }

    const layerOf = new Map();
    for (const node of sortedNodes) {
      let layer = 0;
      for (const pred of (preds.get(node) || [])) {
        if (layerOf.has(pred)) {
          layer = Math.max(layer, layerOf.get(pred) + 1);
        }
      }
      layerOf.set(node, layer);
    }

    // 階層ごとのノード一覧（初期順序はRFC番号順）
    const layers = [];
    for (const node of sortedNodes) {
      const layer = layerOf.get(node);
      while (layers.length <= layer) {
        layers.push([]);
      }
      layers[layer].push(node);
    }

    // 座標の割り当てと、辺の交差を減らすための並べ替え（先行ノードのX座標の平均順）
    const { NODE_W, NODE_H, H_GAP, V_GAP, MARGIN } = RfcHistoryGraphUi;
    const positions = new Map();
    const assignX = (layerNodes, layerIndex) => {
      const width = layerNodes.length * (NODE_W + H_GAP) - H_GAP;
      layerNodes.forEach((node, i) => {
        positions.set(node, {
          x: -width / 2 + i * (NODE_W + H_GAP),
          y: layerIndex * (NODE_H + V_GAP),
        });
      });
    };
    layers.forEach((layerNodes, layerIndex) => {
      if (layerIndex > 0) {
        const barycenter = (node) => {
          const xs = (preds.get(node) || [])
            .filter(pred => positions.has(pred))
            .map(pred => positions.get(pred).x);
          if (xs.length === 0) {
            return Number.MAX_SAFE_INTEGER;  // 先行ノードなしは右端へ（番号順を維持）
          }
          return xs.reduce((a, b) => a + b, 0) / xs.length;
        };
        const keys = new Map(layerNodes.map(node => [node, barycenter(node)]));
        layerNodes.sort((a, b) => keys.get(a) - keys.get(b) || parseInt(a) - parseInt(b));
      }
      assignX(layerNodes, layerIndex);
    });

    // 全体を正の座標へ平行移動
    let minX = Infinity;
    positions.forEach(pos => { minX = Math.min(minX, pos.x); });
    positions.forEach(pos => { pos.x += MARGIN - minX; pos.y += MARGIN; });

    let maxX = 0, maxY = 0;
    positions.forEach(pos => {
      maxX = Math.max(maxX, pos.x + NODE_W);
      maxY = Math.max(maxY, pos.y + NODE_H);
    });
    return {
      positions: positions,
      width: maxX + MARGIN,
      height: maxY + MARGIN,
    };
  }

  _svgElem(tag, attrs) {
    const elem = document.createElementNS(RfcHistoryGraphUi.SVG_NS, tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      elem.setAttribute(key, value);
    }
    return elem;
  }

  _renderSvg(layout, edges) {
    const { NODE_W, NODE_H } = RfcHistoryGraphUi;
    const svg = this._svgElem('svg', { 'class': 'rfc-history-svg' });

    // 矢印マーカーの定義
    const defs = this._svgElem('defs');
    for (const [id, color] of [['rfc-history-arrow-obs', '#d9534f'], ['rfc-history-arrow-upd', '#4a89dc']]) {
      const marker = this._svgElem('marker', {
        id: id, viewBox: '0 0 10 10', refX: 9, refY: 5,
        markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse',
      });
      marker.appendChild(this._svgElem('path', { d: 'M 0 0 L 10 5 L 0 10 z', fill: color }));
      defs.appendChild(marker);
    }
    svg.appendChild(defs);

    // パン・ズーム用のグループ
    const panGroup = this._svgElem('g');
    svg.appendChild(panGroup);

    // 辺の描画（矢印は 古いRFC → 新しいRFC を指す）
    for (const edge of edges) {
      const src = layout.positions.get(edge.src);
      const dst = layout.positions.get(edge.dst);
      if (!src || !dst) {
        continue;
      }
      // 廃止と更新の両方の関係がある場合に重ならないよう少しずらす
      const offset = (edge.type === 'obs') ? -3 : 3;
      const x1 = src.x + NODE_W / 2 + offset;
      const y1 = src.y + NODE_H;
      const x2 = dst.x + NODE_W / 2 + offset;
      const y2 = dst.y;
      const bend = Math.max(20, Math.min(40, Math.abs(y2 - y1) / 2));
      // 現在のRFCに直接つながる辺は強調して表示する
      const isCurrentEdge = (edge.src === this.rfcNumber || edge.dst === this.rfcNumber);
      const path = this._svgElem('path', {
        d: `M ${x1} ${y1} C ${x1} ${y1 + bend}, ${x2} ${y2 - bend}, ${x2} ${y2}`,
        'class': `rfc-history-edge rfc-history-edge-${edge.type}`
          + (isCurrentEdge ? ' rfc-history-edge-current' : ''),
        'marker-end': `url(#rfc-history-arrow-${edge.type})`,
      });
      panGroup.appendChild(path);
    }

    // ノードの描画
    const statusColorMapper = {
      'Informational': '#f0ad4e',
      'Experimental': '#f0ad4e',
      'Best Common Practice': '#d9534f',
      'Best Current Practice': '#d9534f',
      'Proposed Standard': '#17a2b8',
      'Draft Standard': '#17a2b8',
      'Internet Standard': '#28a745',
      'Historic': '#868e96',
    };
    // 現在のRFCと直接つながっているRFCの集合（それ以外のノードは半透明で表示する）
    const currentDatum = this.data[this.rfcNumber] || {};
    const directNeighbors = new Set();
    for (const key of [RfcIndexJsonElem.OBSOLETES, RfcIndexJsonElem.OBSOLETED_BY,
                       RfcIndexJsonElem.UPDATES, RfcIndexJsonElem.UPDATED_BY]) {
      for (const neighbor of (currentDatum[key] || [])) {
        directNeighbors.add(neighbor);
      }
    }
    layout.positions.forEach((pos, node) => {
      const datum = this.data[node] || {};
      const status = datum[RfcIndexJsonElem.CURRENT_STATUS] || 'Unknown';
      const isCurrent = (node === this.rfcNumber);
      const isDimmed = (!isCurrent && !directNeighbors.has(node));

      const link = this._svgElem('a', { href: this._getRfcHref(node) });
      link.setAttribute('class', 'rfc-history-node'
        + (isCurrent ? ' rfc-history-node-current' : '')
        + (isDimmed ? ' rfc-history-node-dimmed' : ''));
      link.dataset.rfcNumber = node;

      const title = this._svgElem('title');
      title.textContent = `RFC ${node}（${status}）の概要を表示`;
      link.appendChild(title);

      // クリック時はページ遷移せず、概要パネルを表示する。
      // ただし、Ctrl/Cmdキーなどを押した別タブで開く操作は既定の動作に任せる
      link.addEventListener('click', (evt) => {
        if (evt.ctrlKey || evt.metaKey || evt.shiftKey || evt.altKey) {
          return;
        }
        evt.preventDefault();
        this._showDetail(node);
      });

      link.appendChild(this._svgElem('rect', {
        x: pos.x, y: pos.y, width: NODE_W, height: NODE_H, rx: 6,
        stroke: statusColorMapper[status] || '#888888',
      }));
      const text = this._svgElem('text', {
        x: pos.x + NODE_W / 2, y: pos.y + NODE_H / 2,
        'text-anchor': 'middle', 'dominant-baseline': 'central',
      });
      text.textContent = `RFC ${node}`;
      link.appendChild(text);
      panGroup.appendChild(link);
    });

    this.panGroup = panGroup;
    return svg;
  }

  _applyView() {
    const { tx, ty, scale } = this.view;
    this.panGroup.setAttribute('transform', `translate(${tx}, ${ty}) scale(${scale})`);
  }

  // 現在のRFCが画面中央付近に来るように表示位置を初期化する
  _resetView() {
    const viewportW = this.canvas.clientWidth;
    const viewportH = this.canvas.clientHeight;
    // 全体が収まるスケールにする。ただし文字が読めなくなるほどは縮小せず、
    // 収まらない分は地図のようにドラッグで移動して見られるようにする
    const scale = Math.max(0.75, Math.min(1,
      viewportW / this.layoutResult.width, viewportH / this.layoutResult.height));
    const current = this.layoutResult.positions.get(this.rfcNumber);
    this.view.scale = scale;
    if (this.layoutResult.width * scale <= viewportW) {
      // 全体が収まる場合はグラフ全体をセンタリングする
      this.view.tx = (viewportW - this.layoutResult.width * scale) / 2;
    } else {
      // 収まらない場合は現在のRFCを中央にする
      this.view.tx = viewportW / 2 - (current.x + RfcHistoryGraphUi.NODE_W / 2) * scale;
    }
    if (this.layoutResult.height * scale <= viewportH) {
      this.view.ty = (viewportH - this.layoutResult.height * scale) / 2;
    } else {
      this.view.ty = Math.min(0, viewportH / 2 - (current.y + RfcHistoryGraphUi.NODE_H / 2) * scale);
    }
    this._applyView();
  }

  // ドラッグによる移動と、マウスホイールによる拡大縮小
  _setupPanZoom(canvas) {
    let dragging = null;
    this.suppressClick = false;
    canvas.addEventListener('pointerdown', (evt) => {
      this.suppressClick = false;
      dragging = { x: evt.clientX, y: evt.clientY, moved: false };
    });
    window.addEventListener('pointermove', (evt) => {
      if (!dragging) {
        return;
      }
      const dx = evt.clientX - dragging.x;
      const dy = evt.clientY - dragging.y;
      // わずかな移動はクリック操作とみなし、ドラッグを開始しない
      if (!dragging.moved && Math.abs(dx) + Math.abs(dy) < 3) {
        return;
      }
      dragging.moved = true;
      canvas.classList.add('rfc-history-grabbing');
      this.view.tx += dx;
      this.view.ty += dy;
      dragging.x = evt.clientX;
      dragging.y = evt.clientY;
      this._applyView();
    });
    const endDrag = () => {
      if (dragging && dragging.moved) {
        this.suppressClick = true;
      }
      dragging = null;
      canvas.classList.remove('rfc-history-grabbing');
    };
    window.addEventListener('pointerup', endDrag);
    window.addEventListener('pointercancel', endDrag);
    // ドラッグ直後のclickイベントでリンク遷移・ダイアログクローズしないようにする
    this.dialogClickHandler = (evt) => {
      if (this.suppressClick) {
        this.suppressClick = false;
        evt.preventDefault();
        evt.stopPropagation();
      }
    };
    canvas.addEventListener('click', this.dialogClickHandler, true);

    canvas.addEventListener('wheel', (evt) => {
      evt.preventDefault();
      const factor = (evt.deltaY < 0) ? 1.15 : 1 / 1.15;
      const newScale = Math.min(RfcHistoryGraphUi.SCALE_MAX,
        Math.max(RfcHistoryGraphUi.SCALE_MIN, this.view.scale * factor));
      const rect = canvas.getBoundingClientRect();
      const cx = evt.clientX - rect.left;
      const cy = evt.clientY - rect.top;
      // カーソル位置を中心に拡大縮小する
      this.view.tx = cx - (cx - this.view.tx) * (newScale / this.view.scale);
      this.view.ty = cy - (cy - this.view.ty) * (newScale / this.view.scale);
      this.view.scale = newScale;
      this._applyView();
    }, { passive: false });
  }

  // RFCページのリンク先。RFC2220未満は自サイト内に存在しないためIETFのサイトへ
  _getRfcHref(rfcNumber) {
    if (parseInt(rfcNumber) < 2220) {
      return `https://datatracker.ietf.org/doc/html/rfc${rfcNumber}`;
    }
    return `./rfc${rfcNumber}.html`;
  }

  // 要約JSONの場所（data/8000/rfc8446-summary.json のように1000件ごとのディレクトリに入っている）
  _getSummaryUrl(rfcNumber) {
    const dir = String(Math.floor(parseInt(rfcNumber) / 1000) * 1000).padStart(4, '0');
    return `../data/${dir}/rfc${rfcNumber}-summary.json`;
  }

  // JSONの取得（存在しない場合や通信エラーの場合はnullを返す）
  async _fetchJson(url) {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        return null;
      }
      return await response.json();
    } catch (e) {
      return null;
    }
  }

  // 全RFCの日本語タイトル（初回のみ取得する）
  async _fetchTitles() {
    if (this.titles === null) {
      this.titles = await this._fetchJson(RfcHistoryGraphUi.FETCH_TITLE_FILENAME) || {};
    }
    return this.titles;
  }

  // 指定したRFCの要約（一度取得したものは再利用する）
  async _fetchSummary(rfcNumber) {
    if (!this.summaries.has(rfcNumber)) {
      const obj = await this._fetchJson(this._getSummaryUrl(rfcNumber));
      const summary = (obj && Array.isArray(obj[RfcSummaryJsonElem.SUMMARY]))
        ? obj[RfcSummaryJsonElem.SUMMARY].join('') : null;
      this.summaries.set(rfcNumber, summary);
    }
    return this.summaries.get(rfcNumber);
  }

  // ノードクリック時に、そのRFCの概要パネルを表示する
  async _showDetail(rfcNumber) {
    this.detailRfcNumber = rfcNumber;
    this._renderDetail(rfcNumber, null, null, true);

    const [titles, summary] = await Promise.all([
      this._fetchTitles(),
      this._fetchSummary(rfcNumber),
    ]);
    // 取得中に別のノードがクリックされていた場合は、表示を上書きしない
    if (this.detailRfcNumber !== rfcNumber) {
      return;
    }
    this._renderDetail(rfcNumber, titles[rfcNumber], summary, false);
  }

  _hideDetail() {
    this.detailRfcNumber = null;
    this.detailPanel.classList.add('hidden');
  }

  _renderDetail(rfcNumber, title, summary, isLoading) {
    const datum = this.data[rfcNumber] || {};
    const status = datum[RfcIndexJsonElem.CURRENT_STATUS];
    const wg = datum[RfcIndexJsonElem.WG];
    const isCurrent = (rfcNumber === this.rfcNumber);

    const panel = this.detailPanel;
    panel.innerHTML = `
      <div class="rfc-history-detail-head">
        <strong class="rfc-history-detail-number"></strong>
        <span class="rfc-history-detail-badges"></span>
        <button type="button" class="rfc-history-detail-close" title="閉じる">&times;</button>
      </div>
      <div class="rfc-history-detail-title"></div>
      <div class="rfc-history-detail-summary"></div>
      <div class="rfc-history-detail-actions"></div>
    `;
    panel.querySelector('.rfc-history-detail-number').textContent = `RFC ${rfcNumber}`;

    // ステータスとWorkingGroupのバッジ
    const badges = panel.querySelector('.rfc-history-detail-badges');
    if (status) {
      const badge = document.createElement('span');
      badge.className = `badge badge-pill badge-${RFC_STATUS_BADGE_CLASS[status] || 'light'}`;
      badge.textContent = status;
      badges.appendChild(badge);
    }
    if (wg) {
      const badge = document.createElement('span');
      badge.className = 'badge badge-primary';
      badge.textContent = wg;
      badges.appendChild(badge);
    }

    // タイトルと要約（未取得・未作成のときは代替の文言を表示する）
    const domTitle = panel.querySelector('.rfc-history-detail-title');
    const domSummary = panel.querySelector('.rfc-history-detail-summary');
    if (isLoading) {
      domSummary.textContent = '読み込み中...';
      domSummary.classList.add('rfc-history-detail-note');
    } else {
      domTitle.textContent = title || '';
      if (summary) {
        domSummary.textContent = summary;
      } else {
        domSummary.textContent = 'このRFCの要約はまだありません。';
        domSummary.classList.add('rfc-history-detail-note');
      }
    }

    // RFCページへ移動するボタン
    const actions = panel.querySelector('.rfc-history-detail-actions');
    if (isCurrent) {
      const note = document.createElement('span');
      note.classList.add('rfc-history-detail-note');
      note.textContent = '現在表示しているRFCです。';
      actions.appendChild(note);
    } else {
      const button = document.createElement('a');
      button.className = 'btn btn-primary btn-sm';
      button.href = this._getRfcHref(rfcNumber);
      button.textContent = (parseInt(rfcNumber) < 2220)
        ? `RFC ${rfcNumber} をIETFのサイトで開く` : `RFC ${rfcNumber} のページを開く`;
      actions.appendChild(button);
    }

    panel.querySelector('.rfc-history-detail-close')
      .addEventListener('click', () => this._hideDetail());
    panel.classList.remove('hidden');
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
