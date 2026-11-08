# raw扱いの英文に関する調査（2026-11-08）

RFC 7925のトラストアンカーストアの定義を起点として、7,705 RFCの翻訳JSONを横断検査しました。
句点と省略記号が続く `....`、数列・識別子・引用符に隣接する同記号を、図表判定が目次の点線と誤認していました。
原文はRFC Editorの公開TXTと照合しました。実際の図表、通信ログ、XML、フィールド形式は英文のまま保持します。

38 RFC・47段落に対訳を追加しました（通常の文章45段落、XMLから切り出した説明文2段落）。
RFC 6330では、途中で改ページにより分かれていた後続段落も結合しています。
英語本文の内容・順序、文書メタデータ、変更対象外の段落が保持されていることを機械的に検証しました。

## 修正箇所

| RFC | 段落数 | 生成HTMLの修正箇所 |
| --- | ---: | --- |
| 2707 | 2 | [箇所1](../html/rfc2707.html#3-4-Monitoring-Job-Progress-p4), [箇所2](../html/rfc2707.html#3-4-Monitoring-Job-Progress-p6) |
| 2848 | 1 | [箇所1](../html/rfc2848.html#1--Introduction-p15) |
| 2914 | 1 | [箇所1](../html/rfc2914.html#4--The-role-of-the-standards-process-p3) |
| 3034 | 1 | [箇所1](../html/rfc3034.html#3--Special-characteristics-of-Frame-Relay-Switches-p1) |
| 3075 | 1 | [箇所1](../html/rfc3075.html#10-0-Definitions-p8) |
| 3090 | 1 | [箇所1](../html/rfc3090.html#1-2-1-Determining-the-closest-security-root-p3) |
| 3098 | 1 | [箇所1](../html/rfc3098.html#A-1-The-classic-Pyramid-p1) |
| 3260 | 1 | [箇所1](../html/rfc3260.html#2--Terminology-Related-to-Service-Level-Agreements-SLAs-p1) |
| 3381 | 2 | [箇所1](../html/rfc3381.html#4-1-job-collation-type-type2-enum-p6), [箇所2](../html/rfc3381.html#4-1-job-collation-type-type2-enum-p8) |
| 3551 | 1 | [箇所1](../html/rfc3551.html#4-3-Guidelines-for-Sample-Based-Audio-Encodings-p3) |
| 3871 | 1 | [箇所1](../html/rfc3871.html#2-11-1--Logging-Facility-Uses-Protocols-Subject-To-Open-Review-p8) |
| 3961 | 1 | [箇所1](../html/rfc3961.html#5-1--A-Key-Derivation-Function-p13) |
| 3970 | 1 | [箇所1](../html/rfc3970.html#3-4--Hop-Information-p2) |
| 4187 | 1 | [箇所1](../html/rfc4187.html#7--Key-Generation-p13) |
| 4192 | 1 | [箇所1](../html/rfc4192.html#1--Introduction-p1) |
| 4257 | 1 | [箇所1](../html/rfc4257.html#1-2--SDHSONET-Overview-p13) |
| 4614 | 1 | [箇所1](../html/rfc4614.html#6-2--Difficult-Network-Environments-p11) |
| 4677 | 1 | [箇所1](../html/rfc4677.html#8-3--Internet-Drafts-p2) |
| 4851 | 1 | [箇所1](../html/rfc4851.html#3-4--Determining-Peer-Id-and-Server-Id-p3) |
| 4949 | 1 | [箇所1](../html/rfc4949.html#4--Definitions-p672) |
| 5123 | 1 | [箇所1](../html/rfc5123.html#2-2--First-Example-Manual-Intervention-in-the-Path-Choice-p4) |
| 5863 | 1 | [箇所1](../html/rfc5863.html#2-2--Choosing-a-DKIM-Tag-for-the-Assessment-Identifier-p4) |
| 6120 | 1 | [箇所1](../html/rfc6120.html#1-4--Terminology-p17) |
| 6121 | 1 | [箇所1](../html/rfc6121.html#1-5--Terminology-p6) |
| 6330 | 2 | [箇所1](../html/rfc6330.html#5-3-1--Introduction-p2), [箇所2](../html/rfc6330.html#5-3-1--Introduction-p3) |
| 6510 | 1 | [箇所1](../html/rfc6510.html#2--Path-Messages-p2) |
| 6534 | 2 | [箇所1](../html/rfc6534.html#3-4--Metric-Definition-p1), [箇所2](../html/rfc6534.html#6--Loss-Episode-Metrics-Derived-from-Bi-Packet-Loss-Probing-p1) |
| 6648 | 1 | [箇所1](../html/rfc6648.html#Appendix-A--Background-p4) |
| 6709 | 5 | [箇所1](../html/rfc6709.html#3-2-2--Local-Use-p9), [箇所2](../html/rfc6709.html#3-2-3--Multi-Site-Experiments-p2), [箇所3](../html/rfc6709.html#3-6--Protocol-Parameter-Registration-p2), [箇所4](../html/rfc6709.html#4-1--Version-Numbers-p5), [箇所5](../html/rfc6709.html#4-5--Cryptographic-Agility-p2) |
| 6873 | 1 | [箇所1](../html/rfc6873.html#6--Text-Tool-Considerations-p2) |
| 7182 | 1 | [箇所1](../html/rfc7182.html#1-1--Differences-from-RFC-6622-p5) |
| 7414 | 1 | [箇所1](../html/rfc7414.html#7-3--Difficult-Network-Environments-p11) |
| 7924 | 1 | [箇所1](../html/rfc7924.html#Appendix-A--Example-p10) |
| 7925 | 1 | [箇所1](../html/rfc7925.html#2--Terminology-p8) |
| 8413 | 1 | [箇所1](../html/rfc8413.html#3-2--What-State-is-Held-p1) |
| 8499 | 1 | [箇所1](../html/rfc8499.html#10--General-DNSSEC-p26) |
| 8512 | 2 | [箇所1](../html/rfc8512.html#A-2--Carrier-Grade-NAT-CGN-p5), [箇所2](../html/rfc8512.html#A-1--Traditional-NAT44-p4) |
| 8667 | 1 | [箇所1](../html/rfc8667.html#2-4-3--Prefix-Length-Prefix-p2) |

## 再発防止と検証

- `Paragraph._without_prose_ellipses`：文章中の4点省略記号を判定用にのみ除外し、英語本文の省略記号自体は保持します。ページ番号付きの点線、実際の目次、図表・コードの判定は保持します。
- `python3 tools/check_raw_prose.py --check`：この誤分類を全RFCから読み取り専用で再検査します。修正後は候補0件です。
- 原文照合、JSON解析、全修正RFCの翻訳lint、新規指摘なしの確認、47段落の生成HTMLの対訳照合、250テストが完了しました。
- ブラウザでRFC 7925のPC・モバイル対訳、RFC 6330の結合段落、RFC 8512のXMLと説明文の分離、RFC 6120の文字参照が文字列として表示されることを確認しました。

本調査の自動検査は4点省略記号に関わる誤分類を対象とします。すべてのraw段落について、別の原因による文章混在や未翻訳がないと保証するものではありません。
