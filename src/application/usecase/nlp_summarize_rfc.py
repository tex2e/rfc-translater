# ------------------------------------------------------------------------------
# RFCの要約を生成するプログラム
# ------------------------------------------------------------------------------

import re
import datetime
from pprint import pprint
from lxml import etree  # pip install lxml
from ...domain.services.rfcutils import RfcUtils
from ...domain.services.rfcfile import RfcFile
from ...domain.valueobject.rfc import RfcXmlElem, RfcSummaryJsonElem, IRfc, Rfc
from ...infrastructure.repository.rfcjsontransrepository import IRfcJsonTransRepository
from ...infrastructure.repository.rfcjsondatasummaryrepository import IRfcJsonDataSummaryRepository
# ChatGPT
from ...domain.services.nlputils import openai, ChatGPT


class SummarizeRfcType:
    TITLE = 'title'
    ABSTRACT = 'abstract'


RFC8650 = 8650  # RFCがXML形式に対応した最小RFC番号（それ以前はTXT形式しか存在しない）


def summarize_rfc(rfc: IRfc,
                  rfc_json_trans_repo: IRfcJsonTransRepository,
                  rfc_json_data_summary_repo: IRfcJsonDataSummaryRepository,
                  args):
    """RFCの要約作成"""

    assert isinstance(rfc, IRfc)
    assert isinstance(rfc, Rfc)  # Draft版以外のみ対応
    assert isinstance(rfc_json_trans_repo, IRfcJsonTransRepository)
    assert isinstance(rfc_json_data_summary_repo, IRfcJsonDataSummaryRepository)

    print(f'[*] summarize_rfc({rfc.get_id()})')

    # GPTのモデル名の正式名称を取得
    gptmodel = ChatGPT.get_exact_model_name(args.chatgpt)

    # RFC翻訳済みかの判定
    rfc_title = rfc_json_trans_repo.get_title(rfc)
    if not rfc_title:
        print('[!] RFC翻訳が未実施です。先に翻訳作業を完了させてください！')
        return False

    # RFC要約済みかの判定
    rfc_current_gptmodel = None
    if rfc_json := rfc_json_data_summary_repo.find(rfc):
        rfc_current_model = rfc_json[RfcSummaryJsonElem.MODEL]
        rfc_current_gptmodel = ChatGPT.get_exact_model_name(rfc_current_model)
        if rfc_current_gptmodel == ChatGPT.MODEL35 and gptmodel == ChatGPT.MODEL4:
            print(f"[*] RFCの要約結果(旧GPTバージョン)を新GPTバージョンの結果で上書きします。")
        else:
            print(f"[-] RFCの要約結果がすでに存在します！")
            return False

    # ChatGPTが対象のRFCの知識を持っているかの判定
    # 2024/3時点で
    # ・ChatGPT-3.5 は2021/9までの情報しか持っていない
    # ・ChatGPT-4 は2023/12までの情報しか持っていない
    chatgpt_has_knowledge = False
    if int(rfc.get_id()) >= RFC8650:
        rfc_url = RfcFile.get_url_rfc_xml(rfc)
        page = RfcUtils.fetch_url(rfc_url)
        page_content = RfcUtils.remove_namespace_from_xml(page.content)
        tree = etree.XML(page_content)
        date_month = None
        date_months = tree.xpath(f'/{RfcXmlElem.RFC}/{RfcXmlElem.FRONT}/{RfcXmlElem.DATE}/@month')
        date_year = None
        date_years = tree.xpath(f'/{RfcXmlElem.RFC}/{RfcXmlElem.FRONT}/{RfcXmlElem.DATE}/@year')
        if len(date_months) > 0:
            date_month = int(date_months[0])
        if len(date_years) > 0:
            date_year = int(date_years[0])
        if date_month and date_year:
            # TRAINING DATAの期間内であればChatGPTが持っている知識のみで要約を作成する
            # https://platform.openai.com/docs/models/continuous-model-upgrades
            if datetime.datetime(date_year, date_month, 1) <= datetime.datetime(2023, 12, 1):
                chatgpt_has_knowledge = True

    # RFC番号で翻訳方法の判定
    if int(rfc.get_id()) < RFC8650:
        summarize_rfc_by = SummarizeRfcType.TITLE
    elif int(rfc.get_id()) >= RFC8650 and chatgpt_has_knowledge:
        summarize_rfc_by = SummarizeRfcType.TITLE
    else:
        summarize_rfc_by = SummarizeRfcType.ABSTRACT
        print(f"[*] ChatGPTのモデルを旧バージョン(3.5)に変更します。")
        gptmodel = ChatGPT.MODEL35  # 概要を要約するときはGPT3.5を常に使用する

    # RFC要約済みかの再判定
    if rfc_current_gptmodel == ChatGPT.MODEL35 and gptmodel == ChatGPT.MODEL35:
        print(f"[-] RFCの要約結果がすでに存在します！")
        return False

    # プロンプトの作成
    if summarize_rfc_by == SummarizeRfcType.TITLE:
        print(f'[+] summarized by "title"')
        prompts = _summarize_rfc_by_title(rfc, rfc_title, gptmodel)
    else:
        print(f'[+] summarized by "abstract"')
        prompts = _summarize_rfc_by_abstract(rfc, rfc_title, gptmodel)

    print(f"[+] gptmodel: {gptmodel}")
    print(f"[+] prompts:")
    pprint(prompts)
    print(f"")
    if args.force or RfcUtils.yes_no_input(f"[?] 上記の内容でChatGPTに質問します。よろしいですか？"):
        pass
    else:
        return False

    # メッセージ作成
    messages = []
    messages.append({"role": "system", "content": "You are a helpful assistant that translates English to Japanese."})
    for prompt in prompts:
        messages.append({"role": "user", "content": prompt})

    # リクエスト作成
    response = openai.chat.completions.create(
        model=gptmodel,
        messages=messages,
        temperature=0
    )

    # GPTからの応答の表示
    text = response.choices[0].message.content
    print(f"[+] " + "-" * 80)
    print(f"[+] output: \n{text}")
    print(f"[+] " + "-" * 80)
    print(f"")

    if args.force or RfcUtils.yes_no_input(f"上記の内容はRFC {rfc.get_id()}の内容ですか？"):
        pass
    else:
        return False

    # GPTからの要約結果をJSON化
    dt_now = datetime.datetime.now()
    obj = {
        RfcSummaryJsonElem.NUMBER: rfc.get_id(),
        RfcSummaryJsonElem.MODEL: gptmodel,
        RfcSummaryJsonElem.CREATED_AT: dt_now.isoformat(),
        RfcSummaryJsonElem.SUMMARY: []
    }
    splitted_texts = re.split(r'\n\n+', text)
    for splitted_text in splitted_texts:
        obj[RfcSummaryJsonElem.SUMMARY].append(splitted_text)

    # RFC要約の出力
    rfc_json_data_summary_repo.save(rfc, obj)
    return True

def _summarize_rfc_by_title(rfc: IRfc, rfc_title: str, gptmodel: str = ChatGPT.MODEL35):
    """指定したRFC番号をChatGPTに要約させる"""
    # GPTへ送信するプロンプト作成
    return (f"{rfc_title} についての要約と目的を技術者の視点から2行でまとめてください。",)

def _summarize_rfc_by_abstract(rfc: IRfc, rfc_title: str, gptmodel: str = ChatGPT.MODEL35):
    """指定したRFCの概要(Abstract)をChatGPTに要約させる"""
    page = RfcUtils.fetch_url(RfcFile.get_url_rfc_xml(rfc))
    page_content = RfcUtils.remove_namespace_from_xml(page.content)
    tree = etree.XML(page_content)

    rfc_abstract = tree.xpath(f'/{RfcXmlElem.RFC}/{RfcXmlElem.FRONT}/{RfcXmlElem.ABSTRACT}//text()')
    if not rfc_abstract or len(rfc_abstract) == 0:
        return False

    rfc_abstract_text = re.sub(r'\s+', ' ', ' '.join(rfc_abstract).strip())

    prompt1 = f"次の英語の文章を日本語でまとめてください。出力形式はですます調で、簡潔に3行以内で要約してください\n\n"
    prompt2 = f"{rfc_abstract_text}"
    return (prompt1, prompt2)
