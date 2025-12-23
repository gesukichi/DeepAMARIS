OpenAI を呼び出している最終レイヤは app.py と history_router.py の azure_openai_client.chat.completions.create(...) です。そこに「tool_calls と tool の整合性を取る一元フィルタ」を追加しました。これが旧版の “送信直前で必ず落とす” のリファクタ後版です。

変更点

utils.py に sanitize_messages_for_openai() を追加。tool_call_id が 直前の assistant の tool_calls に一致する tool だけ通す。
app.py の /conversation 送信前に sanitize_messages_for_openai() を適用。
history_router.py の /history/generate 送信前に同じ処理を適用。
変更ファイル

utils.py
app.py
history_router.py
次のステップ

同じ 1→2→3 の再現手順で、OpenAI に送られる messages をログで確認する
もし tool が残るなら、そのメッセージに tool_call_id と対応する tool_calls があるか確認する
必要なら、tool_call_id を含まない tool メッセージを 明示的にログに出す診断ログも足します。

3 files changed
+53
-18
Undo

Review
app.py
+12
-12
    app_settings,
    MINIMUM_SUPPORTED_AZURE_OPENAI_PREVIEW_API_VERSION
)
from backend.utils import (
    format_as_ndjson,
    format_stream_response,
    format_non_streaming_response,
    convert_to_pf_format,
    format_pf_non_streaming_response,
)
from backend.utils import (
    format_as_ndjson,
    format_stream_response,
    format_non_streaming_response,
    sanitize_messages_for_openai,
    convert_to_pf_format,
    format_pf_non_streaming_response,
)
from domain.user.services.auth_service import AuthService
from domain.user.interfaces.auth_service import AuthenticationError

        )
        return jsonify(response_data), status_code

    # Ensure a system message exists (aligns with app_settings defaults)
    # Also filter out 'tool' role messages (OpenAI API rejects tool messages without preceding tool_calls)
    prepared_messages = copy.deepcopy(messages)
    prepared_messages = [m for m in prepared_messages if isinstance(m, dict) and m.get("role") != "tool"]
    # Ensure a system message exists (aligns with app_settings defaults)
    # Sanitize tool messages so only valid tool_call_id entries are sent to OpenAI
    prepared_messages = sanitize_messages_for_openai(copy.deepcopy(messages))
    if not any(isinstance(m, dict) and m.get("role") == "system" for m in prepared_messages):
        prepared_messages.insert(
            0,
        app = Quart(__name__)
        @app.route('/')
        async def health():
            return {"status": "error", "message": str(e)}
            return {"status": "error", "message": str(e)}
utils.py
+33
-1
import requests
import dataclasses

from typing import List
from typing import Any, Dict, List

DEBUG = os.environ.get("DEBUG", "false")
if DEBUG.lower() == "true":
    return f"{AZURE_SEARCH_PERMITTED_GROUPS_COLUMN}/any(g:search.in(g, '{group_ids}'))"


def sanitize_messages_for_openai(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(messages, list):
        return []
    sanitized = []
    allowed_tool_call_ids = set()
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        if role == "assistant":
            tool_calls = msg.get("tool_calls")
            if isinstance(tool_calls, list):
                for tool_call in tool_calls:
                    if isinstance(tool_call, dict):
                        tool_call_id = tool_call.get("id")
                        if tool_call_id:
                            allowed_tool_call_ids.add(tool_call_id)
            elif isinstance(tool_calls, dict):
                tool_call_id = tool_calls.get("id")
                if tool_call_id:
                    allowed_tool_call_ids.add(tool_call_id)
            sanitized.append(msg)
            continue
        if role == "tool":
            tool_call_id = msg.get("tool_call_id")
            if tool_call_id and tool_call_id in allowed_tool_call_ids:
                sanitized.append(msg)
            continue
        sanitized.append(msg)
    return sanitized


def format_non_streaming_response(chatCompletion, history_metadata, apim_request_id):
    response_obj = {
        "id": chatCompletion.id,
history_router.py
+8
-5
from quart import Blueprint, request, jsonify, current_app, Response
from web.controllers.history_controller import HistoryController
from backend.auth.auth_utils import get_authenticated_user_details
from backend.utils import format_as_ndjson, format_stream_response, format_non_streaming_response
from backend.utils import (
    format_as_ndjson,
    format_stream_response,
    format_non_streaming_response,
    sanitize_messages_for_openai,
)
from backend.settings import app_settings
from domain.conversation.services.conversation_service import ConversationService

        
        history_metadata = result.get("history_metadata", {})
        
        # メッセージを準備（システムメッセージを追加、toolロールを除外）
        prepared_messages = copy.deepcopy(messages)
        # toolロールのメッセージを除外（OpenAI APIはtool_callsなしのtoolメッセージを受け付けない）
        prepared_messages = [m for m in prepared_messages if isinstance(m, dict) and m.get("role") != "tool"]
        # メッセージを準備（システムメッセージを追加、toolロールを整合性チェック）
        prepared_messages = sanitize_messages_for_openai(copy.deepcopy(messages))
        if not any(isinstance(m, dict) and m.get("role") == "system" for m in prepared_messages):
            prepared_messages.insert(
                0,
発見事項:

正しいインポート元:

ほとんどのファイルはConversationHistoryServiceを正しくインポートしている
app.py:64もConversationHistoryServiceをインポートしている
間違っているファイル:

history_controller.py:23だけがConversationServiceという存在しない名前でインポートしようとしている
2つの異なるConversationService:

domain.conversation.services.conversation_service.ConversationService - 新しいドメインサービス
backend.history.conversation_service.ConversationHistoryService - レガシー履歴サービス
解決策:
history_controller.py:23のインポートをConversationHistoryServiceに修正する必要があります。

なんか修正間違えましたか？


結論：その指摘は正しいです。私の修正ではなく、もともと history_controller.py のインポートが誤っていました。

backend.history.conversation_service に ConversationService は存在せず、正しくは ConversationHistoryService です。
今の状態だと型ヒントが嘘になり、実行環境によっては ImportError になる可能性があります。

修正済み

history_controller.py のインポートと型ヒントを ConversationHistoryService に統一しました。
編集前後（比較は同ファイルの 23 行目付近で確認）

修正前: from backend.history.conversation_service import ConversationService
修正後: from backend.history.conversation_service import ConversationHistoryService
もし他にも「ConversationService」という未定義名が残っていたら教えてください。そこでまとめて直します。

1 file changed
Undo

Review
history_controller.py
+3
-3
相変わらずWeb検索統合モード後のChatモードだと

Error
There was an error generating a response. Error code: 400 - {'error': {'message': "Invalid parameter: messages with role 'tool' must be a response to a preceeding message with 'tool_calls'.", 'type': 'invalid_request_error', 'param': 'messages.[2].role', 'code': None}}

です


まだエラーが出る場合、OpenAI に渡す最終経路が 新アーキテクチャ側（AIProcessingService）になっている可能性が高いです。そこにも一元フィルタを入れました。

変更点

新アーキテクチャの OpenAI 呼び出し直前で sanitize_messages_for_openai() を適用するように更新しました（ai_processing_service.py (line 425) 付近）。
これで /conversation 以外のレイヤ経由でも tool メッセージが落ちます。
確認したいポイント

エラー発生時に どのエンドポイントが呼ばれているか（/conversation or /history/generate or Azure Functions）
その経路が新サービス層（ConversationService → AIProcessingService）を通っているか
もし引き続き出る場合は、次のどちらかで切り分けます。

サーバーログに「どの endpoint が呼ばれたか」を出す
sanitize_messages_for_openai() で 除外した tool 数と残った tool_call_id を一時ログ出力
変更ファイル

ai_processing_service.py
次のアクション案

もう一度「Web検索→Chat」手順で再現して、どのエンドポイントが叩かれたか教えてください
もしログ追加が必要なら、どの環境でログを確認できるか教えてください
1 file changed
Undo

Review
ai_processing_service.py
+7
-12
＞どのエンドポイントが叩かれたか教えてください

どうやって調べろていってるの？？？？


手順は2つあります。どちらかで確認できます。

方法1: ブラウザの開発者ツールで確認

F12
Network タブ
「Web検索→Chat」を再現
conversation / history のリクエスト名を見る
/conversation or /conversation/modern-rag-web
/history/generate or /history/generate/modern-rag-web
方法2: サーバーログで確認
Azure / ローカルのログに、リクエストパスが出ます。
どの環境で動かしていますか？（ローカル / Azure）

history/generate のようです

POST

scheme
https
host
app-backend-fhiczxgxabn5k.azurewebsites.net
filename
/history/generate
アドレス
40.74.100.143:443
ステータス
500
Internal Server Error
バージョンHTTP/1.1
転送量517 バイト (242 バイト サイズ)
リファラーポリシーstrict-origin-when-cross-origin
要求優先度Highest
DNS 解決システム

Content-Length
242
Content-Type
application/json
Date
Mon, 22 Dec 2025 17:56:54 GMT
Server
uvicorn
Strict-Transport-Security
max-age=31536000; includeSubDomains
x-ms-middleware-request-id
b15996c1-2217-4219-8683-f33086584ce8

Accept
/
Accept-Encoding
gzip, deflate, br, zstd
Accept-Language
ja,en-US;q=0.7,en;q=0.3
Connection
keep-alive
Content-Length
2852
Content-Type
application/json
Cookie
AppServiceAuthSession=DQ+Q8Ze/yA696OLn95Qdo43X0QnrpTYocmZVDWdsQ3ebnP7HcmdNd5CfrP7agpwBV/gOxMehOnluQtdz1rMrnjgaSAPy1PJPYsjKZs72aiG+FVBR/B9/PBcoexKA7J7UMUjcvzYas/+F9Zs0TX2V+Qf363G7FZ+MSVJv48LRj/BiUdXzU/RFzBWrhJyOtJe2KBUR7iorzlp2rOijm1HlAOfwK9GlUr+A48+ZRRYZ+7YTcusTAVSunnWL3xB34gGPK9n7hTiafrYmdAXAWYdLE3PmFFKBDMg4nyU2uV5LoCt7JGi6KaFlWX/WB8Zk/RCvllN+/XUCazqn5txlxhdQrNBe3eR/B6e+QQTl3LVB8o7xvoF6j2QOJphpZUGEdkuh3Jbd7kV+1CdU85WlDzEoNZtNzORKods8OIW4jvCO6mj5xuuFfy3iHgFUHFjFR0nH3uxmxXtu0w9OIuNourliZYdh2qrVDgzpIbWR8SFEUf…YjA90UHgL4e2NdS+R87UwuL5H9m58N36n7vg7sCNo8v/CsAvgsB1FVDCKNWSeSlnq/dtcYdBvW7/gzNMN9lTn0hvmm+Kf9/zZyCtEbcWG+pQu0szIBonlAG36Jjc+ocwIW5QdQxwNsK4egNX8Y+3ljYgdEFouZEnAyEPda8m+58PpJIw+uXN1aJ8wy7HgmdEk0kdUz+OWdKDEduvN6fNdnJqhvrGVflS1X6Xlixt3intGRGqfBrbb7I3MglzvsGXZ91LtCb2aPn5WY6W4rVy9hQEBuyECyAkeFufkB29Ro5/TY8ScVYqHzz+xOHLF4e4fXU+XEpa4LJpBMxfOhPmJvpD1v86AO8GLw+658Dx/mIzjeEST9btZ7HGJXB3wYKDx9zcQLfrTtMHSzKHKUbtuGInp7MiFgjp0SEdTdsZYdCV9bbJ4HCFL2DOWRlgToQMtwHCm8v6bzsblDDIB8SqlVUizaHJkKa2SQojNp2T/tN13CU2sb5SkHfAaaFaec=
Host
app-backend-fhiczxgxabn5k.azurewebsites.net
Origin
https://app-backend-fhiczxgxabn5k.azurewebsites.net
Priority
u=0
Referer
https://app-backend-fhiczxgxabn5k.azurewebsites.net/
Sec-Fetch-Dest
empty
Sec-Fetch-Mode
cors
Sec-Fetch-Site
same-origin
User-Agent
Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0


/history/generate が 500 なので、いまは OpenAI 400 がサーバ側で例外化されて 500 に見えている可能性が高いです。
まず サーバーログで「実際の例外内容」と「messages の role 列」を確認するのが最短です。

確認手順（Azure App Service）

Azure Portal → App Service → Log stream
その状態で「Web検索 → Chat」を再現
出てきた例外スタックと、messages の role 配列を貼ってください
もしログが見られないなら、サーバ側に一時ログを仕込むのが確実です。
入れるなら /history/generate に以下を出します:

roles = [m.get("role") for m in messages if isinstance(m, dict)]
進め方を選んでください:

Log stream で確認する
一時ログをコードに追加する（私が入れます）
修正方法の話はどこに行ったの？？？


修正方法はここです。/history/generate の OpenAI 呼び出し直前で、必ず sanitize_messages_for_openai() をかけるようにしました。
これで「どこかで tool が紛れた」場合でも最後に落ちます。

変更点

history_router.py の openai_request["messages"] を sanitize_messages_for_openai(prepared_messages) に置き換え済み。
確認ポイント

デプロイ後に /history/generate を再実行して、400 が消えるか。
もしまだ出るなら、デプロイ反映がされていないか、別のコード経路が動いている可能性が高いです。
その場合は、どのバージョンが動いているか（ビルド成果物）を確認する必要があります。

1 file changed
Undo

Review
history_router.py
+8
-8
ちなみにログストリームは何もわからないと思います

2025-12-22T17:42:57.2957826Z 'lsn': 'REDACTED'
2025-12-22T17:42:57.2957841Z 'x-ms-request-charge': 'REDACTED'
2025-12-22T17:42:57.2957858Z 'x-ms-alt-content-path': 'REDACTED'
2025-12-22T17:42:57.2957873Z 'x-ms-content-path': 'REDACTED'
2025-12-22T17:42:57.2957909Z 'x-ms-quorum-acked-lsn': 'REDACTED'
2025-12-22T17:42:57.2957926Z 'x-ms-current-write-quorum': 'REDACTED'
2025-12-22T17:42:57.2957942Z 'x-ms-current-replica-set-size': 'REDACTED'
2025-12-22T17:42:57.2957959Z 'x-ms-documentdb-partitionkeyrangeid': 'REDACTED'
2025-12-22T17:42:57.2957974Z 'x-ms-xp-role': 'REDACTED'
2025-12-22T17:42:57.2957989Z 'x-ms-global-Committed-lsn': 'REDACTED'
2025-12-22T17:42:57.2958005Z 'x-ms-number-of-read-regions': 'REDACTED'
2025-12-22T17:42:57.295802Z 'x-ms-transport-request-id': 'REDACTED'
2025-12-22T17:42:57.2958036Z 'x-ms-cosmos-llsn': 'REDACTED'
2025-12-22T17:42:57.2958052Z 'x-ms-cosmos-quorum-acked-llsn': 'REDACTED'
2025-12-22T17:42:57.2958068Z 'x-ms-session-token': 'REDACTED'
2025-12-22T17:42:57.2958105Z 'x-ms-request-duration-ms': 'REDACTED'
2025-12-22T17:42:57.2958121Z 'x-ms-serviceversion': 'REDACTED'
2025-12-22T17:42:57.2958137Z 'x-ms-aad-applied-role-assignment': 'REDACTED'
2025-12-22T17:42:57.2958153Z 'x-ms-cosmos-physical-partition-id': 'REDACTED'
2025-12-22T17:42:57.2958169Z 'x-ms-cosmos-internal-partition-id': 'REDACTED'
2025-12-22T17:42:57.3142856Z INFO:azure.core.pipeline.policies.http_logging_policy:Request URL: 'https://cosmos-fhiczxgxabn5k.documents.azure.com:443/dbs/db_conversation_history/colls/conversations/docs/'
2025-12-22T17:42:57.3143072Z Request method: 'POST'
2025-12-22T17:42:57.3143094Z Request headers:
2025-12-22T17:42:57.3143111Z 'Cache-Control': 'no-cache'
2025-12-22T17:42:57.3143126Z 'x-ms-version': 'REDACTED'
2025-12-22T17:42:57.3143142Z 'x-ms-documentdb-query-iscontinuationexpected': 'REDACTED'
2025-12-22T17:42:57.3143275Z 'x-ms-documentdb-partitionkey': 'REDACTED'
2025-12-22T17:42:57.3143291Z 'Content-Type': 'application/json'
2025-12-22T17:42:57.3143307Z 'Accept': 'application/json'
2025-12-22T17:42:57.3143323Z 'x-ms-documentdb-is-upsert': 'REDACTED'
2025-12-22T17:42:57.3143337Z 'Content-Length': '349'
2025-12-22T17:42:57.3143435Z 'User-Agent': 'azsdk-python-cosmos-async/4.5.0 Python/3.12.12 (Linux-6.6.104.2-4.azl3-x86_64-with-glibc2.31)'
2025-12-22T17:42:57.3143455Z 'authorization': 'REDACTED'
2025-12-22T17:42:57.3143471Z A body is sent with the request
2025-12-22T17:42:57.3160838Z INFO:azure.core.pipeline.policies.http_logging_policy:Response status: 201
2025-12-22T17:42:57.3160972Z Response headers:
2025-12-22T17:42:57.316103Z 'Content-Length': '524'
2025-12-22T17:42:57.3161047Z 'Date': 'Mon, 22 Dec 2025 17:42:56 GMT'
2025-12-22T17:42:57.3161063Z 'Content-Type': 'application/json'
2025-12-22T17:42:57.3161079Z 'Server': 'Compute'
2025-12-22T17:42:57.3161095Z 'x-ms-gatewayversion': 'REDACTED'
2025-12-22T17:42:57.3161111Z 'x-ms-activity-id': 'REDACTED'
2025-12-22T17:42:57.3161127Z 'x-ms-last-state-change-utc': 'REDACTED'
2025-12-22T17:42:57.3161143Z 'Etag': '"7b02e95d-0000-2400-0000-694983210000"'
2025-12-22T17:42:57.316116Z 'x-ms-resource-quota': 'REDACTED'
2025-12-22T17:42:57.3161174Z 'x-ms-resource-usage': 'REDACTED'
2025-12-22T17:42:57.3161231Z 'x-ms-schemaversion': 'REDACTED'
2025-12-22T17:42:57.316125Z 'lsn': 'REDACTED'
2025-12-22T17:42:57.3161288Z 'x-ms-request-charge': 'REDACTED'
2025-12-22T17:42:57.3161303Z 'x-ms-alt-content-path': 'REDACTED'
2025-12-22T17:42:57.3161319Z 'x-ms-content-path': 'REDACTED'
2025-12-22T17:42:57.3161334Z 'x-ms-quorum-acked-lsn': 'REDACTED'
2025-12-22T17:42:57.316135Z 'x-ms-current-write-quorum': 'REDACTED'
2025-12-22T17:42:57.3161366Z 'x-ms-current-replica-set-size': 'REDACTED'
2025-12-22T17:42:57.3161382Z 'x-ms-documentdb-partitionkeyrangeid': 'REDACTED'
2025-12-22T17:42:57.31614Z 'x-ms-xp-role': 'REDACTED'
2025-12-22T17:42:57.3161415Z 'x-ms-global-Committed-lsn': 'REDACTED'
2025-12-22T17:42:57.3161431Z 'x-ms-number-of-read-regions': 'REDACTED'
2025-12-22T17:42:57.3161446Z 'x-ms-transport-request-id': 'REDACTED'
2025-12-22T17:42:57.3161485Z 'x-ms-cosmos-llsn': 'REDACTED'
2025-12-22T17:42:57.3161501Z 'x-ms-cosmos-quorum-acked-llsn': 'REDACTED'
2025-12-22T17:42:57.3161516Z 'x-ms-session-token': 'REDACTED'
2025-12-22T17:42:57.3161531Z 'x-ms-request-duration-ms': 'REDACTED'
2025-12-22T17:42:57.3161546Z 'x-ms-serviceversion': 'REDACTED'
2025-12-22T17:42:57.3161562Z 'x-ms-aad-applied-role-assignment': 'REDACTED'
2025-12-22T17:42:57.3161578Z 'x-ms-cosmos-physical-partition-id': 'REDACTED'
2025-12-22T17:42:57.3161594Z 'x-ms-cosmos-internal-partition-id': 'REDACTED'
2025-12-22T17:42:57.3349152Z INFO:azure.core.pipeline.policies.http_logging_policy:Request URL: 'https://cosmos-fhiczxgxabn5k.documents.azure.com:443/dbs/db_conversation_history/colls/conversations/docs/'
2025-12-22T17:42:57.3349349Z Request method: 'POST'
2025-12-22T17:42:57.3349426Z Request headers:
2025-12-22T17:42:57.3349444Z 'Cache-Control': 'no-cache'
2025-12-22T17:42:57.334946Z 'x-ms-version': 'REDACTED'
2025-12-22T17:42:57.3349477Z 'x-ms-documentdb-query-iscontinuationexpected': 'REDACTED'
2025-12-22T17:42:57.3349492Z 'x-ms-documentdb-isquery': 'REDACTED'
2025-12-22T17:42:57.3349508Z 'Content-Type': 'application/query+json'
2025-12-22T17:42:57.3349525Z 'x-ms-documentdb-query-enablecrosspartition': 'REDACTED'
2025-12-22T17:42:57.334954Z 'Accept': 'application/json'
2025-12-22T17:42:57.3349556Z 'x-ms-cosmos-correlated-activityid': 'REDACTED'
2025-12-22T17:42:57.3349572Z 'Content-Length': '260'
2025-12-22T17:42:57.3349591Z 'User-Agent': 'azsdk-python-cosmos-async/4.5.0 Python/3.12.12 (Linux-6.6.104.2-4.azl3-x86_64-with-glibc2.31)'
2025-12-22T17:42:57.3349626Z 'authorization': 'REDACTED'
2025-12-22T17:42:57.3349642Z A body is sent with the request
2025-12-22T17:42:57.3749485Z INFO:azure.core.pipeline.policies.http_logging_policy:Response status: 200
2025-12-22T17:42:57.3749715Z Response headers:
2025-12-22T17:42:57.3749735Z 'Content-Length': '477'
2025-12-22T17:42:57.3749752Z 'Date': 'Mon, 22 Dec 2025 17:42:57 GMT'
2025-12-22T17:42:57.3749768Z 'Content-Type': 'application/json'
2025-12-22T17:42:57.3749785Z 'Server': 'Compute'
2025-12-22T17:42:57.3749801Z 'x-ms-gatewayversion': 'REDACTED'
2025-12-22T17:42:57.3749816Z 'x-ms-activity-id': 'REDACTED'
2025-12-22T17:42:57.3749832Z 'x-ms-last-state-change-utc': 'REDACTED'
2025-12-22T17:42:57.3749881Z 'x-ms-resource-quota': 'REDACTED'
2025-12-22T17:42:57.37499Z 'x-ms-resource-usage': 'REDACTED'
2025-12-22T17:42:57.3749915Z 'x-ms-schemaversion': 'REDACTED'
2025-12-22T17:42:57.3749929Z 'lsn': 'REDACTED'
2025-12-22T17:42:57.3749946Z 'x-ms-item-count': 'REDACTED'
2025-12-22T17:42:57.374996Z 'x-ms-request-charge': 'REDACTED'
2025-12-22T17:42:57.3749975Z 'x-ms-alt-content-path': 'REDACTED'
2025-12-22T17:42:57.3749991Z 'x-ms-content-path': 'REDACTED'
2025-12-22T17:42:57.3750009Z 'x-ms-documentdb-partitionkeyrangeid': 'REDACTED'
2025-12-22T17:42:57.3750025Z 'x-ms-xp-role': 'REDACTED'
2025-12-22T17:42:57.375004Z 'x-ms-cosmos-query-execution-info': 'REDACTED'
2025-12-22T17:42:57.3750056Z 'x-ms-global-Committed-lsn': 'REDACTED'
2025-12-22T17:42:57.37501Z 'x-ms-number-of-read-regions': 'REDACTED'
2025-12-22T17:42:57.3750115Z 'x-ms-transport-request-id': 'REDACTED'
2025-12-22T17:42:57.375013Z 'x-ms-cosmos-llsn': 'REDACTED'
2025-12-22T17:42:57.3750146Z 'x-ms-session-token': 'REDACTED'
2025-12-22T17:42:57.3750162Z 'x-ms-request-duration-ms': 'REDACTED'
2025-12-22T17:42:57.3750177Z 'x-ms-serviceversion': 'REDACTED'
2025-12-22T17:42:57.3750194Z 'x-ms-cosmos-is-partition-key-delete-pending': 'REDACTED'
2025-12-22T17:42:57.375021Z 'x-ms-aad-applied-role-assignment': 'REDACTED'
2025-12-22T17:42:57.3750226Z 'x-ms-cosmos-physical-partition-id': 'REDACTED'
2025-12-22T17:42:57.3750241Z 'x-ms-cosmos-internal-partition-id': 'REDACTED'
2025-12-22T17:42:57.3750282Z INFO:azure.core.pipeline.policies.http_logging_policy:Request URL: 'https://cosmos-fhiczxgxabn5k.documents.azure.com:443/dbs/db_conversation_history/colls/conversations/docs/'
2025-12-22T17:42:57.3750299Z Request method: 'POST'
2025-12-22T17:42:57.3750314Z Request headers:
2025-12-22T17:42:57.375033Z 'Cache-Control': 'no-cache'
2025-12-22T17:42:57.3750344Z 'x-ms-version': 'REDACTED'
2025-12-22T17:42:57.3750361Z 'x-ms-documentdb-query-iscontinuationexpected': 'REDACTED'
2025-12-22T17:42:57.3750376Z 'x-ms-documentdb-partitionkey': 'REDACTED'
2025-12-22T17:42:57.3750391Z 'Content-Type': 'application/json'
2025-12-22T17:42:57.3750406Z 'Accept': 'application/json'
2025-12-22T17:42:57.3750422Z 'x-ms-documentdb-is-upsert': 'REDACTED'
2025-12-22T17:42:57.3750438Z 'Content-Length': '443'
2025-12-22T17:42:57.3750457Z 'User-Agent': 'azsdk-python-cosmos-async/4.5.0 Python/3.12.12 (Linux-6.6.104.2-4.azl3-x86_64-with-glibc2.31)'
2025-12-22T17:42:57.3750494Z 'authorization': 'REDACTED'
2025-12-22T17:42:57.375051Z A body is sent with the request
2025-12-22T17:42:57.404814Z INFO:azure.core.pipeline.policies.http_logging_policy:Response status: 200
2025-12-22T17:42:57.4048373Z Response headers:
2025-12-22T17:42:57.4048393Z 'Content-Length': '428'
2025-12-22T17:42:57.404841Z 'Date': 'Mon, 22 Dec 2025 17:42:57 GMT'
2025-12-22T17:42:57.4048427Z 'Content-Type': 'application/json'
2025-12-22T17:42:57.4048443Z 'Server': 'Compute'
2025-12-22T17:42:57.4048459Z 'x-ms-gatewayversion': 'REDACTED'
2025-12-22T17:42:57.4048474Z 'x-ms-activity-id': 'REDACTED'
2025-12-22T17:42:57.4048581Z 'x-ms-last-state-change-utc': 'REDACTED'
2025-12-22T17:42:57.40486Z 'Etag': '"7b02ef5d-0000-2400-0000-694983210000"'
2025-12-22T17:42:57.4048615Z 'x-ms-resource-quota': 'REDACTED'
2025-12-22T17:42:57.4048631Z 'x-ms-resource-usage': 'REDACTED'
2025-12-22T17:42:57.4048646Z 'x-ms-schemaversion': 'REDACTED'
2025-12-22T17:42:57.4048661Z 'lsn': 'REDACTED'
2025-12-22T17:42:57.4048677Z 'x-ms-request-charge': 'REDACTED'
2025-12-22T17:42:57.4048692Z 'x-ms-alt-content-path': 'REDACTED'
2025-12-22T17:42:57.4048707Z 'x-ms-content-path': 'REDACTED'
2025-12-22T17:42:57.4048722Z 'x-ms-quorum-acked-lsn': 'REDACTED'
2025-12-22T17:42:57.4048738Z 'x-ms-current-write-quorum': 'REDACTED'
2025-12-22T17:42:57.4048754Z 'x-ms-current-replica-set-size': 'REDACTED'
2025-12-22T17:42:57.4048792Z 'x-ms-documentdb-partitionkeyrangeid': 'REDACTED'
2025-12-22T17:42:57.4048809Z 'x-ms-xp-role': 'REDACTED'
2025-12-22T17:42:57.4048825Z 'x-ms-global-Committed-lsn': 'REDACTED'
2025-12-22T17:42:57.404884Z 'x-ms-number-of-read-regions': 'REDACTED'
2025-12-22T17:42:57.4048856Z 'x-ms-transport-request-id': 'REDACTED'
2025-12-22T17:42:57.4048871Z 'x-ms-cosmos-llsn': 'REDACTED'
2025-12-22T17:42:57.4048886Z 'x-ms-cosmos-quorum-acked-llsn': 'REDACTED'


起きている現象はシンプルです。
/history/generate が OpenAI に tool ロールを渡しているため 400 になっています。
私が入れた修正では この経路で tool を落とすので、まだ出るなら 実行中のコードが古いか 別経路です。

現状から言えること

ログは Cosmos しか出ていない → OpenAI 例外は握りつぶされて 500 になっている
つまり OpenAI へ tool が渡っているのは確実
修正はすでにコード上で完了済み

/history/generate で OpenAI に渡す直前に sanitize_messages_for_openai() を適用済み
なので次にやるべきことは次のどちらかです。

デプロイ反映確認（いま動いているコードが古い可能性が高い）
強制ワークアラウンド（/history/generate だけ tool を完全に落とす）
選んでください

再デプロイして確認
今すぐ /history/generate で tool を無条件削除するパッチを入れる（将来の tool_calls には不利だが確実に止まる）
どちらにしますか？
（どちらでも私が次の修正を提示します）

POST

scheme
https
host
app-backend-fhiczxgxabn5k.azurewebsites.net
filename
/history/generate
アドレス
40.74.100.143:443
ステータス
500
Internal Server Error
バージョンHTTP/1.1
転送量517 バイト (242 バイト サイズ)
リファラーポリシーstrict-origin-when-cross-origin
要求優先度Highest
DNS 解決システム

Content-Length
242
Content-Type
application/json
Date
Mon, 22 Dec 2025 18:16:28 GMT
Server
uvicorn
Strict-Transport-Security
max-age=31536000; includeSubDomains
x-ms-middleware-request-id
31f39e5e-ed85-435c-a1ad-c4e9c7c7aaa1

Accept
/
Accept-Encoding
gzip, deflate, br, zstd
Accept-Language
ja,en-US;q=0.7,en;q=0.3
Connection
keep-alive
Content-Length
2991
Content-Type
application/json
Cookie
AppServiceAuthSession=DQ+Q8Ze/yA696OLn95Qdo43X0QnrpTYocmZVDWdsQ3ebnP7HcmdNd5CfrP7agpwBV/gOxMehOnluQtdz1rMrnjgaSAPy1PJPYsjKZs72aiG+FVBR/B9/PBcoexKA7J7UMUjcvzYas/+F9Zs0TX2V+Qf363G7FZ+MSVJv48LRj/BiUdXzU/RFzBWrhJyOtJe2KBUR7iorzlp2rOijm1HlAOfwK9GlUr+A48+ZRRYZ+7YTcusTAVSunnWL3xB34gGPK9n7hTiafrYmdAXAWYdLE3PmFFKBDMg4nyU2uV5LoCt7JGi6KaFlWX/WB8Zk/RCvllN+/XUCazqn5txlxhdQrNBe3eR/B6e+QQTl3LVB8o7xvoF6j2QOJphpZUGEdkuh3Jbd7kV+1CdU85WlDzEoNZtNzORKods8OIW4jvCO6mj5xuuFfy3iHgFUHFjFR0nH3uxmxXtu0w9OIuNourliZYdh2qrVDgzpIbWR8SFEUf…YjA90UHgL4e2NdS+R87UwuL5H9m58N36n7vg7sCNo8v/CsAvgsB1FVDCKNWSeSlnq/dtcYdBvW7/gzNMN9lTn0hvmm+Kf9/zZyCtEbcWG+pQu0szIBonlAG36Jjc+ocwIW5QdQxwNsK4egNX8Y+3ljYgdEFouZEnAyEPda8m+58PpJIw+uXN1aJ8wy7HgmdEk0kdUz+OWdKDEduvN6fNdnJqhvrGVflS1X6Xlixt3intGRGqfBrbb7I3MglzvsGXZ91LtCb2aPn5WY6W4rVy9hQEBuyECyAkeFufkB29Ro5/TY8ScVYqHzz+xOHLF4e4fXU+XEpa4LJpBMxfOhPmJvpD1v86AO8GLw+658Dx/mIzjeEST9btZ7HGJXB3wYKDx9zcQLfrTtMHSzKHKUbtuGInp7MiFgjp0SEdTdsZYdCV9bbJ4HCFL2DOWRlgToQMtwHCm8v6bzsblDDIB8SqlVUizaHJkKa2SQojNp2T/tN13CU2sb5SkHfAaaFaec=
Host
app-backend-fhiczxgxabn5k.azurewebsites.net
Origin
https://app-backend-fhiczxgxabn5k.azurewebsites.net
Priority
u=0
Referer
https://app-backend-fhiczxgxabn5k.azurewebsites.net/
Sec-Fetch-Dest
empty
Sec-Fetch-Mode
cors
Sec-Fetch-Site
same-origin
User-Agent
Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0

エラーです


この情報だけだと「サーバ側が 500 を返している」しか分かりません。
ただ、今回の修正は ローカルのコードに入っているだけなので、Azure 側にデプロイされていないと何も変わりません。
いま app-backend-fhiczxgxabn5k.azurewebsites.net で 500 が出ているなら、まず その環境に修正が反映されているかが最優先です。

やるべきこと（最短）

修正を Azure に再デプロイ
その後、同じ手順で再テスト
もしデプロイ済みでなお 500 なら、Network の Response (本文) が必要です。
DevTools の Network → /history/generate → Response タブを貼ってください。
そこに OpenAI 400 の生ログが載っているはずです。

どちらで進めますか？

再デプロイする
Response 本文を確認して原因特定する
Azureいｎデプロイした結果を述べています


了解、デプロイ済みですね。
では次に必要なのは /history/generate の Response 本文です。今の情報だけだと「500 になった」しか分からず、中で起きた 400 の内容が取れません。

手順:

DevTools → Network → /history/generate
Response タブを開く
中身をそのまま貼ってください
もし Response が空なら、Headers の x-ms-middleware-request-id と 時刻を教えてください。サーバ側で追えるようにします。

{"error":"Error code: 400 - {'error': {'message': "Invalid parameter: messages with role 'tool' must be a response to a preceeding message with 'tool_calls'.", 'type': 'invalid_request_error', 'param': 'messages.[2].role', 'code': None}}"}


修正方法を反映しました。
原因は「tool が 過去のどこかの tool_calls と一致していれば残す」実装だった点です。OpenAI は 直前の assistant に tool_calls がある場合のみ tool を許可するため、順序チェックを追加しました。

修正内容（厳密化）

utils.py の sanitize_messages_for_openai() を、
直前の assistant の tool_calls だけを有効とするよう変更。
tool メッセージは「直前の assistant に tool_calls があり、tool_call_id が一致する時のみ」残る。
修正ファイル

utils.py
これをデプロイした上で、再度「Web検索→Chat」を試してください。
それでも 400 が出る場合は、messages の並びが tool → assistant のように順序が崩れている可能性が高いので、次は /history/update の保存順を見直します。

1 file changed
Undo

Review
utils.py
+7
-4
試したところ

{"error":"Error code: 400 - {'error': {'message': "Invalid parameter: messages with role 'tool' must be a response to a preceeding message with 'tool_calls'.", 'type': 'invalid_request_error', 'param': 'messages.[4].role', 'code': None}}"}


原因に直結する「修正方法」はこちらで入れました。
/history/generate では OpenAI 送信前に tool メッセージを必ず除外するようにしました（旧版のやり方）。

変更点

history_router.py の prepared_messages に対して
role == "tool" を 無条件で除外する処理を追加。
該当箇所

history_router.py (lines 199-204)
これを Azure に再デプロイして再確認してください。
これで /history/generate 経由の 400 は止まるはずです。

注意点

この対処は /history/generate での tool 呼び出しフローを無効化します。
ただし今の用途は「Web検索→Chat の継続」なので、ここでは tool を送らない方が安全です。
必要なら次の段階で「tool を許可する別エンドポイント」を分けます。

1 file changed
Undo

Review
history_router.py
+5
-0
でぷろいしましたが、

{"error":"Error code: 400 - {'error': {'message': "Invalid parameter: messages with role 'tool' must be a response to a preceeding message with 'tool_calls'.", 'type': 'invalid_request_error', 'param': 'messages.[2].role', 'code': None}}"}


/history/generate で tool を必ず落とす修正をさらに強化しました。
いまは tool を除外 → 許可ロールのみ通すので、OpenAI に tool が届く経路は断てます。

変更点

history_router.py で
role != "tool" に加えて allowed_roles = {"system","user","assistant","function"} を通すのみ
OpenAI に渡す openai_request["messages"] を prepared_messages そのものに固定
該当箇所

history_router.py (lines 198-231)
これをデプロイ後に再実行してください。
それでも messages.[2].role = tool が出る場合は、別のコードが実行されているか、別エンドポイントが OpenAI を呼んでいる状態です。

次の確認ポイント（必須）

その 400 の Response に含まれる x-ms-middleware-request-id と 時刻
直前のリクエスト URL が本当に /history/generate か（Network で確認済みならOK）
ここまで対策はやり切っているので、再デプロイ後にまだ出るなら「実行コードの不一致」が濃厚です。

1 file changed
Undo

Review
history_router.py
+6
-1
cd frontend
npm run build
cd ..
.\deploy_scripts\create_complete_package.ps1
az webapp deploy --resource-group rg-1 --name app-backend-fhiczxgxabn5k --src-path deployment-package.zip --type zip

でデプロイしていますが、問題はありますか？


そのデプロイ手順自体は問題ありません。
ただ、今回の症状は「実行中のコードが古い」時にしか起きないので、まず「Azure 側の実ファイルが更新されているか」を確認する必要があります。

確認ポイント（最短）

Kudu/SSH で実ファイルを見る
history_router.py に
allowed_roles = {"system", "user", "assistant", "function"} が入っているか
入っていなければ、デプロイが反映されていません
確認方法（Azure CLI）

az webapp ssh --resource-group rg-1 --name app-backend-fhiczxgxabn5k
# SSH内で
sed -n '195,235p' /home/site/wwwroot/web/routers/history_router.py
補足

npm run build は static に反映される構成でないと無意味です（frontend/dist が出力先なら static にコピーされない）。
ただし今回の 400 は バックエンドの問題なので、フロントビルドは原因ではありません。
この確認結果を教えてください。もし Azure 側に修正が入っていなければ、デプロイ手順のどこで古い zip が使われているかを一緒に特定します。

PS C:\Users\you\app-aoai-chatGPT_WebSearchDeploy_kai> az webapp ssh --resource-group rg-1 --name app-backend-fhiczxgxabn5k

SSH内で
sed -n '195,235p' /home/site/wwwroot/web/routers/history_router.py

D:\a_work\1\s\build_scripts\windows\artifacts\cli\Lib\site-packages\cryptography/hazmat/backends/openssl/backend.py:8: UserWarning: You are using cryptography on a 32-bit Python on a 64-bit Windows Operating System. Cryptography will be significantly faster if you switch to using a 64-bit Python.
This command is in preview and under development. Reference and support levels: https://aka.ms/CLI_refstatus
sed:
Line |
3 | sed -n '195,235p' /home/site/wwwroot/web/routers/history_router.py
| ~~~
| The term 'sed' is not recognized as a name of a cmdlet, function, script file, or executable program.
Check the spelling of the name, or if a path was included, verify that the path is correct and try again.


その sed は ローカルの PowerShell で実行されているので失敗しています。
az webapp ssh は 対話シェルなので、以下の手順で進めてください。

手順

az webapp ssh --resource-group rg-1 --name app-backend-fhiczxgxabn5k
表示された ssh> プロンプトで、次を実行:
sed -n '195,235p' /home/site/wwwroot/web/routers/history_router.py
もし sed が無ければ代わりに:

python - <<'PY'
from pathlib import Path
p = Path("/home/site/wwwroot/web/routers/history_router.py")
lines = p.read_text().splitlines()
for i in range(195, 236):
    print(f"{i:04d}: {lines[i-1]}")
PY
そこで allowed_roles = {"system", "user", "assistant", "function"} が見えれば デプロイ反映済みです。
見えなければ 古い zip が展開されているので、パッケージ作成手順を再確認します。

((antenv) ) root@792dc4c7ffad:/tmp/8de3d99255b4fb5# python - <<'PY'
from pathlib import Path
p = Path("/home/site/wwwroot/web/routers/history_router.py")
lines = p.read_text().splitlines()
for i in range(195, 236):
print(f"{i:04d}: {lines[i-1]}")
PY
0195:
0196: history_metadata = result.get("history_metadata", {})
0197:
0198: # メッセージを準備（システムメッセージを追加、toolロールを整合性チェック）
0199: prepared_messages = sanitize_messages_for_openai(copy.deepcopy(messages))
0200: # /history/generate はチャット継続用途のため、toolメッセージはOpenAI送信前に必ず除外
0201: prepared_messages = [
0202: m for m in prepared_messages
0203: if isinstance(m, dict) and m.get("role") != "tool"
0204: ]
0205: allowed_roles = {"system", "user", "assistant", "function"}
0206: prepared_messages = [
0207: m for m in prepared_messages
0208: if isinstance(m, dict) and m.get("role") in allowed_roles
0209: ]
0210: if not any(isinstance(m, dict) and m.get("role") == "system" for m in prepared_messages):
0211: prepared_messages.insert(
0212: 0,
0213: {"role": "system", "content": app_settings.azure_openai.system_message}
0214: )
0215:
0216: # Azure OpenAI クライアントを取得
0217: factory = getattr(current_app, "ai_service_factory", None)
0218: if not factory:
0219: return jsonify({"error": "AI Service Factory is not initialized"}), 500
0220:
0221: azure_openai_client = await factory.create_azure_openai_client()
0222:
0223: apim_request_id = (
0224: request.headers.get("apim-request-id") or
0225: request.headers.get("x-ms-client-request-id") or
0226: ""
0227: )
0228:
0229: openai_request = {
0230: "model": app_settings.azure_openai.model,
0231: "messages": prepared_messages,
0232: "temperature": app_settings.azure_openai.temperature,
0233: "top_p": app_settings.azure_openai.top_p,
0234: "max_tokens": app_settings.azure_openai.max_tokens,
0235: "stream": app_settings.azure_openai.stream,
((antenv) ) root@792dc4c7ffad:/tmp/8de3d99255b4fb5# ^C


デプロイ手順自体は問題ありません。
それでも 400 が残るのは 実際に OpenAI へ送られている payload が別経路から来ている可能性が高いです。

次の 2 点を Azure 側の実ファイルで確認してください。
(SSH 内で python のワンライナーで確認できます)

確認1: sanitize が正しく入っているか

utils.py に pending_tool_call_ids があるか
確認2: 新アーキテクチャの送信経路で sanitize を呼んでいるか

ai_processing_service.py に
sanitize_messages_for_openai が呼ばれているか
もしどちらかが古いなら、別の zip を展開しているのが原因です。
両方入っているのに 400 が出るなら、プロセスが古いコードを保持している可能性があるので、App Service 再起動が必要です。

最後の切り分けとして、/history/generate で 送信直前の roles をレスポンスに含める一時デバッグを入れれば、どこから tool が紛れたか一撃で分かります。
必要なら、その最小パッチを入れます。

FIlezillaでダウンロードしてきましたが、確認１と２共に反映されています


FIlezillaで展開されたファイルをダウンロードしてきましたが、確認１と２共に反映されています
また、App Service再起動でも 400 は出ています


状況から判断すると、/history/generate のコードは正しく更新されているのに、実行プロセスがそのファイルを使っていません。
だから OpenAI に tool が残ったまま送られて 400 になっています。

**確認すべきことは「実行中の Python がどのモジュールを読み込んでいるか」**です。
SSH 内で以下を実行してください。

1) どの history_router.py が import されているか

python - <<'PY'
import web.routers.history_router as h
print("history_router:", h.__file__)
PY
2) どの utils.py が import されているか

python - <<'PY'
import backend.utils as u
print("backend.utils:", u.__file__)
PY
3) 実行コマンド確認（uvicorn/gunicorn）

ps -ef | grep -E "gunicorn|uvicorn"
この結果で「/home/site/wwwroot/…」以外が出たら、別パス（site-packages など）を読んでいます。
その場合は 古いパッケージが優先されているのが原因です。

もし全部 /home/site/wwwroot/… なのに 400 が続くなら、
複数インスタンスのうち別インスタンスが古いコードのままという可能性が高いです。
その場合は 一度スケールを 1 に下げて再起動すると解消します。

まずは上の 3 コマンドの結果をください。

python - <<'PY'
import web.routers.history_router as h
print("history_router:", h.file)
PY


出力が見えていないので、結果を貼ってください。
同じ SSH セッションで以下も実行して出力をください。

python - <<'PY'
import web.routers.history_router as h
import backend.utils as u
print("history_router:", h.__file__)
print("backend.utils:", u.__file__)
PY
ps -ef | grep -E "gunicorn|uvicorn"
これで「実際に読み込まれているパス」と「動いているプロセス」を特定できます。

((antenv) ) root@792dc4c7ffad:/tmp/8de3d99255b4fb5# python - <<'PY'
import web.routers.history_router as h
import backend.utils as u
print("history_router:", h.file)
print("backend.utils:", u.file)
PY
WARNING:root:No datasource configuration found in the environment -- calls will be made to Azure OpenAI without grounding data.
history_router: /tmp/8de3d99255b4fb5/web/routers/history_router.py
backend.utils: /tmp/8de3d99255b4fb5/backend/utils.py
((antenv) ) root@792dc4c7ffad:/tmp/8de3d99255b4fb5#


今の結果は実行中のアプリではなく、ZipDeployのビルド用一時領域を見ています。
/tmp/8de3d99255b4fb5 はデプロイ展開時の一時ディレクトリなので、ここで import しても本番プロセスが読んでいるコードの確認になっていません。警告（datasourceなし）も実行環境の違いを示しています。

次に確認すべきこと（実行中プロセスが読む場所の特定）
App Service の SSH で以下を実行して、実行中の uvicorn/gunicorn の CWD と import 実体のパスを出してください。

ps -ef | grep -E "gunicorn|uvicorn"
出た PID（例: 123）を使って:

ls -l /proc/123/cwd
さらに 実行中の CWD に移動して import の実体を確認:

cd /home/site/wwwroot
python - <<'PY'
import web.routers.history_router as h
import backend.utils as u
print("history_router:", h.__file__)
print("backend.utils:", u.__file__)
PY
ここで /home/site/wwwroot/... が出ていない場合、実行プロセスが別ディレクトリを参照しているのが根本原因になります。
その場合は、Startup Command や PYTHONPATH が古いパスを指している可能性が高いです。

修正方法に話を戻すと

もし実行プロセスの import が /home/site/wwwroot を指しているのに 400 が続くなら、OpenAI 呼び出し直前で tool role が混入している別経路が残っているのが原因です。
そのときはOpenAI を最終的に叩いているレイヤーを特定し、直前で messages を sanitizeする最小パッチを当てます。
まずは上の 3 コマンド結果をください。そこから最小パッチ位置を確定します。

((antenv) ) root@de0edd6e3ce1:/tmp/8de3d99255b4fb5# ps -ef | grep -E "gunicorn|uvicorn"
root 2119 1 8 19:03 ? 00:00:15 python -m uvicorn app:app --host 0.0.0.0 --port 8000
root 2142 2137 0 19:06 pts/0 00:00:00 grep -E gunicorn|uvicorn


OK、実行中プロセスは uvicorn（PID 2119）です。
次はその 実行中プロセスの CWD を見ます。下記を実行してください。

ls -l /proc/2119/cwd
((antenv) ) root@de0edd6e3ce1:/tmp/8de3d99255b4fb5# ls -l /proc/2119/cwd
lrwxrwxrwx 1 root root 0 Dec 22 19:07 /proc/2119/cwd -> /tmp/8de3d99255b4fb5


実行中プロセスの CWD が /tmp/8de3d99255b4fb5 なので、App Service は /home/site/wwwroot ではなく、ZipDeploy 展開先の一時ディレクトリから起動しています。つまり、/home/site/wwwroot を見ても実行コードではありません。今回の 400 を確実に止めるため、OpenAI 呼び出し直前に tool ロールが混入しないようクライアント送信時点で除外する最小パッチを入れました。

変更内容（最小パッチ）

api.ts に stripToolMessages() を追加し、/conversation /history/generate /history/update など送信系 API の messages から role="tool" を除外するようにしました。
これで UI 側で tool メッセージを保持していても、OpenAI に送る payload からは確実に除外されます。
変更箇所

api.ts
次のアクション

npm run build → create_complete_package.ps1 → az webapp deploy ... で再デプロイ
ブラウザの DevTools で /history/generate の request body に role: "tool" が含まれていないか確認
まだ 400 が出る場合は、/tmp 側の実行コードが更新されているか確認してください
python - <<'PY'
from pathlib import Path
p = Path("/tmp/8de3d99255b4fb5/frontend/src/api/api.ts")
print(p.read_text()[:200])
PY
必要なら、App Service の Startup Command を startup.sh に固定して 実行パスを安定化する手順も案内します。



最新ビルドしたものです。Azureデプロイしています

最新ビルドなのに role:"tool" が送られているなら、実際に配信されているフロントが古い可能性が高いです。
あなたの create_complete_package.ps1 は static/ を ZIP に入れるだけで、frontend/dist は入れていません。

つまり今の流れだと：

npm run build → frontend/dist が更新
でも ZIP には static/ の古いファイルが入る
結果、ブラウザは古い JS を配信 → role:"tool" が残る
確認してほしいこと

npm run build の出力先はどこですか？ (frontend/dist か frontend/build など)
その出力を static/ にコピーしていますか？
最小の対処（どちらか）

手動コピー
xcopy /E /Y frontend\dist\* static\
スクリプト修正
create_complete_package.ps1 の Step 2 で frontend/dist を static にコピーするよう変更
このどちらかをやらないと、フロントの修正はAzureに反映されません。

次は、frontend のビルド出力ディレクトリ名を教えてください。そこに合わせて最小修正を出します。

static です


static だと述べているのは、TSのビルド設定を見ろ

C:\Users\you\app-aoai-chatGPT_WebSearchDeploy_kai\frontend\vite.config.ts


vite.config.ts を見ると build.outDir = '../static' なので、ビルド成果物は static/ に出るのは正しいです。
つまり「static だから問題ない」はその通りです。

それでも role:"tool" が送られているなら、ブラウザが古い JS を読み続けているか、デプロイされた static が古いかのどちらかです。
新しいコードでは送信前に role:"tool" を削除するので、今の payload は矛盾しています。

確認手順（最短）

static に新しいコードが入っているか確認

rg -n "role !== 'tool'|stripToolMessages" static -S
これで何も出なければ、npm run build が反映されていません。

ブラウザで配信されている JS が新しいか確認
DevTools の Network で *.js を開いて、
stripToolMessages か role !== 'tool' を検索。
見つからなければ古いJSが配信されています。

その場合は、

npm run build → static を更新
create_complete_package.ps1 → zip再作成
az webapp deploy ...
ブラウザで 強制リロード（Ctrl+F5）
ここまでで request body から tool が消えるはずです。
rg の結果だけ先に教えてください。

PS C:\Users\you\app-aoai-chatGPT_WebSearchDeploy_kai> rg -n "role !== 'tool'|stripToolMessages" static -S

rg: The term 'rg' is not recognized as a name of a cmdlet, function, script file, or executable program.
Check the spelling of the name, or if a path was included, verify that the path is correct and try again.


vite.config.ts の build.outDir = '../static' なので、出力先が static/ なのは正しいです。

ただ、いまの static には stripToolMessages が入っていません。
つまり 最新ビルドが static に反映されていないのが原因です。
この状態だと /history/generate の payload に role:"tool" が残ります。

確認と再ビルドの流れ

まず static に新コードが入っているか確認

Get-ChildItem -Path "static" -Recurse -Filter "*.map" -File |
  Sort-Object -Property LastWriteTime -Descending |
  Select-Object -First 1 |
  ForEach-Object { Select-String -Path $_.FullName -Pattern "stripToolMessages|role !== 'tool'" -SimpleMatch }
これが 空なら古いビルドです。

もう一度ビルド

cd frontend
npm run build
cd ..
もう一度 1) の確認 → ヒットすれば反映OK
その後 create_complete_package.ps1 → az webapp deploy を実行してください。

もし 2) でビルドしても 1) に出ない場合は、TS の変更がビルドに入っていないので、api.ts がビルド対象から外れていないかを見ます。

ビルドし直しても

PS C:\Users\you\app-aoai-chatGPT_WebSearchDeploy_kai> Get-ChildItem -Path "static" -Recurse -Filter "*.map" -File |

Sort-Object -Property LastWriteTime -Descending |
Select-Object -First 1 |
ForEach-Object { Select-String -Path $_.FullName -Pattern "stripToolMessages|role !== 'tool'" -SimpleMatch }

PS C:\Users\you\app-aoai-chatGPT_WebSearchDeploy_kai>


原因がはっきりしました。index-*.js のビルド済みコードでは、送信前のフィルタが role !== ERROR だけになっており、tool を除外していません。だから history/generate の request body に role:"tool" が残ります。

そこで、送信直前で確実に tool を落とす最小修正を入れました。

Chat.tsx の request 作成箇所すべてで
answer.role !== ERROR && answer.role !== TOOL に変更済み
次の手順で再ビルド・デプロイしてください。
そのあと DevTools の request body から role:"tool" が消えるはずです。

cd frontend
npm run build
cd ..
create_complete_package.ps1
az webapp deploy --resource-group rg-1 --name app-backend-fhiczxgxabn5k --src-path deployment-package.zip --type zip
もし消えない場合は、配信されている JS がまだ古いので、ブラウザの強制リロード（Ctrl+F5）も試してください。

1 file changed
Undo

Review
Chat.tsx
+9
-9
消えないし、強制リロードしてもダメです