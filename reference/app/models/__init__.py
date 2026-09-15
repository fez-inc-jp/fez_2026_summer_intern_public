"""テーブルモデルの再エクスポート

create_all がテーブルを認識するには、モデルがここから import されている
必要がある (main.py の `from app import models` が読み込み経路)
"""

from app.models.chat import Chat as Chat
