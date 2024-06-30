# ------------------------------------------------------------------------------
# RFCの文章を翻訳するプログラム
# ------------------------------------------------------------------------------

import re
from pprint import pprint
from .rfc_utils import RfcUtils
from ..models.rfc import RfcJsonElem, IRfc
from ..repository.irfcjsondatarepository import IRfcJsonDataRepository
from ..repository.irfcjsontransrepository import IRfcJsonTransRepository
from ..repository.irfcjsontransmidwayrepository import IRfcJsonTransMidwayRepository
from .translater.metatranslater import MyTranslateException
from .translater.seleniumgoogletranslater import TranslatorSeleniumGoogletrans


def trans_rfc(rfc: IRfc,
              rfc_json_data_repo: IRfcJsonDataRepository,
              rfc_json_trans_repo: IRfcJsonTransRepository,
              rfc_json_trans_midway_repo: IRfcJsonTransMidwayRepository,
              args) -> bool:
    """指定したRFCを翻訳する"""

    assert isinstance(rfc, IRfc)
    assert isinstance(rfc_json_data_repo, IRfcJsonDataRepository)
    assert isinstance(rfc_json_trans_repo, IRfcJsonTransRepository)
    assert isinstance(rfc_json_trans_midway_repo, IRfcJsonTransMidwayRepository)

    print(f"[*] trans_rfc({rfc.get_id()})")

    # 途中まで翻訳済みのファイルがあれば復元する
    if obj := rfc_json_trans_midway_repo.find(rfc):
        midway_file = rfc_json_trans_midway_repo.findpath(rfc)
        print(f'[+] found midway file: {midway_file}')
    else:
        obj = rfc_json_data_repo.find(rfc)

    # 翻訳対象の段落数
    total_len = len([con for con in obj[RfcJsonElem.CONTENTS] if not con.get(RfcJsonElem.Contents.RAW)])
    desc = 'RFC %s' % rfc.get_id()
    # Google翻訳
    print(f"[*] Google翻訳で翻訳します")
    translator = TranslatorSeleniumGoogletrans(total=total_len, desc=desc, args=args)
    # translator = TranslatorGoogleV2(total=total_len, desc=desc, args=args)
    # translator = TranslatorChatGPT(total=total_len, desc=desc, args=args)

    try:
        # タイトルの翻訳
        if not obj[RfcJsonElem.TITLE].get(RfcJsonElem.Title.JA):
            titles = obj[RfcJsonElem.TITLE][RfcJsonElem.Title.TEXT].split(' - ', 1)  # "RFC XXXX - Title"
            if len(titles) <= 1:
                obj[RfcJsonElem.TITLE][RfcJsonElem.Title.JA] = "RFC %s" % rfc.get_id()
            else:
                text = titles[1]
                ja = translator.translate(text)
                obj[RfcJsonElem.TITLE][RfcJsonElem.Title.JA] = "RFC %s - %s" % (rfc.get_id(), ja)

        # 段落の翻訳
        for i, obj_contents_i in enumerate(obj[RfcJsonElem.CONTENTS]):

            # 既に翻訳済みの段落はスキップする
            if obj_contents_i.get(RfcJsonElem.Contents.JA):
                translator.increment_progress()  # 進捗+1
                continue

            # 英語原文
            text = obj_contents_i[RfcJsonElem.Contents.TEXT]
            # 英語原文の前文字（箇条書きの記号などを翻訳しないようにするため）
            pre_text = ""
            # 日本語翻訳文
            text_ja = ""
            # 箇条書きのパターン
            # 「-」「o」「*」「+」「$」「A.」「A.1.」「a)」「1)」「(a)」「(1)」「[1]」「[a]」「a.」
            pattern = r'^([\-o\*\+\$] |(?:[A-Z]\.)?(?:\d{1,2}\.)+(?:\d{1,2})? |\(?[0-9a-z]\) |\[[0-9a-z]{1,2}\] |[a-z]\. )(.*)$'

            if obj_contents_i.get(RfcJsonElem.Contents.RAW) is True:
                # 図表は翻訳しない
                obj[RfcJsonElem.CONTENTS][i][RfcJsonElem.Contents.JA] = ''  # 翻訳結果を格納
            elif m := re.match(r'^([a-zA-Z]{1,3}:)$', text):
                # 数式の変数説明は翻訳しない
                text = m[1]
                obj[RfcJsonElem.CONTENTS][i][RfcJsonElem.Contents.JA] = text  # 原文をそのまま格納
                translator.increment_progress()  # 進捗+1
            elif m := re.match(pattern, text):
                # 記号的意味を持つ文字から始まる文は箇条書きなので、その前文字を除外して翻訳する。
                pre_text, text = m[1], m[2]
                # 翻訳の実行
                text_ja = translator.translate(text)
                obj[RfcJsonElem.CONTENTS][i][RfcJsonElem.Contents.JA] = pre_text + text_ja  # 翻訳結果を格納
                translator.increment_progress()  # 進捗+1
            elif m := re.match(r'^Appendix ([A-Z])\. (.*)$', text):
                # 原文がセクション付録の場合
                pre_text, text = (f'付録{m[1]}. ', m[2])
                # 翻訳の実行
                text_ja = translator.translate(text)
                obj[RfcJsonElem.CONTENTS][i][RfcJsonElem.Contents.JA] = pre_text + text_ja  # 翻訳結果を格納
                translator.increment_progress()  # 進捗+1
            else:
                # 通常の本文
                pre_text, text = ('', text)
                # 翻訳の実行
                text_ja = translator.translate(text)
                obj[RfcJsonElem.CONTENTS][i][RfcJsonElem.Contents.JA] = pre_text + text_ja  # 翻訳結果を格納
                translator.increment_progress()  # 進捗+1

        print("", flush=True)

        # 正常終了した時
        # 翻訳成果物をファイルに出力する
        rfc_json_trans_repo.save(rfc, obj)
        output_file = rfc_json_trans_repo.findpath(rfc)
        print(f"[+] Save file: {output_file}")
        # 不要な入力ファイルの削除
        if rfc_json_data_repo.delete(rfc):
            input_file = rfc_json_data_repo.findpath(rfc)
            print(f"[+] Delete file: {input_file}")
        # 不要な中間ファイルの削除
        if rfc_json_trans_midway_repo.delete(rfc):
            midway_file = rfc_json_trans_midway_repo.findpath(rfc)
            print(f"[+] Delete file: {midway_file}")
        return True

    except (MyTranslateException, KeyboardInterrupt, Exception) as e:
        # TimeoutException: ネットワークなどの問題で発生する例外
        # KeyboardInterrupt: ユーザが意図的に処理を停止したときに発生する例外
        print(f'[-] Translator Error! ({RfcUtils.get_now()})')
        print(f'[-] error={e}')

        # 異常終了した時
        # 途中まで翻訳済みのファイルを生成する
        rfc_json_trans_midway_repo.save(rfc, obj)
        print(f"[+] Save file: {midway_file}")
        # 例外をそのまま投げる
        raise

    finally:
        translator.close()


def trans_test(args):
    """翻訳処理の動作確認テスト"""
    # import argparse
    # args = argparse.Namespace()
    # args.chatgpt = ChatGPT.MODEL35
    translator = TranslatorSeleniumGoogletrans(total=1, args=args)
    # translator = TranslatorGoogleV2(total=1, args=args)
    # ja = translator.translate('test sample.')
    # translator = TranslatorChatGPT(total=1, args=args)
    # ja = translator.translate('psk')
    ja = translator.translate('The first stems from the fact that entanglement enables stronger-than-classical correlations, leading to opportunities for tasks that require coordination. As a trivial example, consider the problem of consensus between two nodes who want to agree on the value of a single bit. They can use the quantum network to prepare the state (|00⟩ + |11⟩)/sqrt(2) with each node holding one of the two qubits. Once either of the two nodes performs a measurement, the state of the two qubits collapses to either |00⟩ or |11⟩, so whilst the outcome is random and does not exist before measurement, the two nodes will always measure the same value. We can also build the more general multi-qubit state (|00...⟩ + |11...⟩)/sqrt(2) and perform the same algorithm between an arbitrary number of nodes. These stronger-than-classical correlations generalise to measurement schemes that are more complicated as well.')
    print('[+] result:', ja)
    translator.increment_progress()
