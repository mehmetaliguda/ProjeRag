"""
mssql_source.py
----------------
Onceden indekslenmeyen, canli MSSQL log kaynagi.

Her chat isteginde MSSQL'e YENI bir baglanti acilir (pool KULLANILMAZ),
timestamp_column'a gore azalan sirada (en yeniden eskiye) kucuk batch'ler
halinde kayit cekilir ve qwen2.5:7b-instruct'in context penceresine
guvenle sigacak bir karakter/token butcesi doldurulana kadar birikim
yapilir. Butce dolunca veya max_rows/deneme siniri asilinca cekim durur;
sonsuz dongu veya kontrolsuz OFFSET artisi YOKTUR.

Donen adaylar rerank EDILMEZ: get_multi_room_answer butun kaynaklardan
gelen adaylari TEK bir paylasilan CrossEncoderReranker cagrisiyla
puanlar (bkz. rag_chat.py), boylece kaynak sayisi artsa da LLM cagri
sayisi sabit kalir.
"""

import re
from datetime import datetime
from typing import Any, Dict, List

import pyodbc

from dotenv_rag import get_env_variable
from mssql_crypto import decrypt_password

# ------------------------------------------------------------------
# qwen2.5:7b-instruct icin varsayilan/limit degerler
# ------------------------------------------------------------------
DEFAULT_MAX_CONTEXT_TOKENS = 32768
DEFAULT_RESERVED_OUTPUT_TOKENS = 1024
MAX_RESERVED_OUTPUT_TOKENS = 2048
DEFAULT_RETRIEVAL_TOKENS = 8192
MAX_RETRIEVAL_TOKENS = 12288
CHARS_PER_TOKEN = 3          # token sayaci yoksa muhafazakar tahmin (TR metin icin ~3 char/token)
SAFETY_MARGIN_RATIO = 0.12   # %10-%15 arasi guvenlik payi

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_identifier(name: str, kind: str = "identifier") -> str:
    """table_name/timestamp_column/text_columns icin siki whitelist.

    Bu alanlar SQL Server tarafinda parametreli sorguyla gecirilemez
    (identifier'lar parametre olamaz), bu yuzden dogrudan sorguya
    gomulmeden once burada string dogrulamasi ZORUNLUDUR. Sadece harf,
    rakam ve alt cizgi kabul edilir; rakamla baslayamaz.
    """
    if not isinstance(name, str) or not _IDENTIFIER_RE.match(name):
        raise ValueError(
            f"Gecersiz {kind}: {name!r}. Sadece harf, rakam, alt cizgi "
            "icerebilir ve rakamla baslayamaz."
        )
    return name


def _env_int(name: str, default: int) -> int:
    val = get_env_variable(name)
    if not val:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def compute_safe_retrieval_budget(
    config,
    system_prompt_text: str = "",
    history_text: str = "",
    question_text: str = "",
) -> int:
    """qwen2.5:7b-instruct icin guvenli MSSQL retrieval token butcesini hesaplar.

    Once maksimum context limiti belirlenir (sirasiyla: config.max_context_tokens
    override -> MSSQL_MAX_CONTEXT_TOKENS env -> varsayilan 32768). Bundan sistem
    prompt + gecmis + soru + cevap payi + guvenlik payi dusulur; kalan MSSQL
    retrieval'a ayrilir. Sonuc, config/varsayilan retrieval hedefiyle (en fazla
    MSSQL_MAX_RETRIEVAL_TOKENS / 12288) sinirlanir.
    """
    max_context = getattr(config, "max_context_tokens", None) or _env_int(
        "MSSQL_MAX_CONTEXT_TOKENS", DEFAULT_MAX_CONTEXT_TOKENS
    )

    reserved_output = getattr(config, "reserved_output_tokens", None) or _env_int(
        "MSSQL_RESERVED_OUTPUT_TOKENS", DEFAULT_RESERVED_OUTPUT_TOKENS
    )
    reserved_output = min(reserved_output, MAX_RESERVED_OUTPUT_TOKENS)

    configured_default = getattr(config, "max_retrieval_tokens", None) or _env_int(
        "MSSQL_DEFAULT_RETRIEVAL_TOKENS", DEFAULT_RETRIEVAL_TOKENS
    )
    retrieval_cap = _env_int("MSSQL_MAX_RETRIEVAL_TOKENS", MAX_RETRIEVAL_TOKENS)
    configured_default = min(configured_default, retrieval_cap)

    used_chars = len(system_prompt_text) + len(history_text) + len(question_text)
    used_tokens = -(-used_chars // CHARS_PER_TOKEN)  # ceil bolme

    safety_margin = int(max_context * SAFETY_MARGIN_RATIO)

    available = max_context - used_tokens - reserved_output - safety_margin
    budget = min(configured_default, max(0, available))
    return max(0, budget)


def tokens_to_chars(config, tokens: int) -> int:
    """Token butcesini karaktere cevirir; config'de max_retrieval_chars
    verilmisse token limitine karsilik gelen karakter sinirini asmayacak
    sekilde onunla sinirlar."""
    char_estimate = tokens * CHARS_PER_TOKEN
    max_chars_override = getattr(config, "max_retrieval_chars", None)
    if max_chars_override:
        return min(char_estimate, int(max_chars_override))
    return char_estimate


class MssqlSource:
    """Bir notebook'a bagli canli MSSQL log kaynagi.

    RagRoom/HybridRetriever ile ayni 'retrieve(query, k) -> List[Dict]'
    sozlesmesini saglar (doc_id, content, page, score alanlari), boylece
    get_multi_room_answer kaynak-agnostik calisabilir.
    """

    MAX_FETCH_ATTEMPTS = 20
    DEFAULT_BATCH_SIZE = 200
    DEFAULT_MAX_ROWS = 2000
    CONNECT_TIMEOUT_SECONDS = 5

    def __init__(self, notebook_id: int, config):
        self.notebook_id = notebook_id
        self.config = config
        self.display_name = f"MSSQL Log ({config.table_name})"

    @property
    def room_id(self) -> str:
        return f"mssql:{self.notebook_id}"

    # ------------------------------------------------------------------
    def _connect(self):
        """Her cagrida YENI bir baglanti acar; connection pool kullanilmaz."""
        password = decrypt_password(self.config.password_encrypted)
        driver = get_env_variable("MSSQL_ODBC_DRIVER", "ODBC Driver 18 for SQL Server")
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={self.config.server},{self.config.port or 1433};"
            f"DATABASE={self.config.database_name};"
            f"UID={self.config.username};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )
        return pyodbc.connect(conn_str, timeout=self.CONNECT_TIMEOUT_SECONDS)

    def _validated_columns(self):
        table = validate_identifier(self.config.table_name, "table_name")
        ts_col = validate_identifier(self.config.timestamp_column, "timestamp_column")
        text_cols = self.config.text_columns or []
        if not text_cols:
            raise ValueError("MSSQL config: text_columns bos olamaz.")
        text_cols = [validate_identifier(c, "text_columns") for c in text_cols]
        return table, ts_col, text_cols

    def test_connection(self) -> None:
        """Config kaydetmeden once baglantiyi dogrulamak icin basit bir
        test sorgusu calistirir. Basarisizsa exception firlatir (caller
        400 donup DB'ye yazmamali)."""
        table, _, _ = self._validated_columns()
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT TOP 1 1 FROM {table}")
            cursor.fetchall()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    def retrieve(
        self,
        query: str,
        k: int = 5,
        system_prompt_text: str = "",
        history_text: str = "",
    ) -> List[Dict[str, Any]]:
        """En yeni kayitlardan baslayarak guvenli bir karakter/token
        butcesi icinde aday log kayitlarini doner.

        NOT: Kullanicidan gelen 'query' metni SQL WHERE'e KATILMAZ (SQL
        injection riskini tamamen ortadan kaldirmak icin) - alakalilik
        filtrelemesi cagiran tarafta paylasilan reranker ile yapilir.
        Herhangi bir hata/timeout/bos tablo/yetki sorununda exception
        yerine bos liste donulur ki sistem crash etmesin.
        """
        try:
            table, ts_col, text_cols = self._validated_columns()
        except ValueError as e:
            print(f"[MssqlSource:{self.room_id}] Config hatasi: {e}")
            return []

        budget_tokens = compute_safe_retrieval_budget(
            self.config,
            system_prompt_text=system_prompt_text,
            history_text=history_text,
            question_text=query,
        )
        char_budget = tokens_to_chars(self.config, budget_tokens)
        if char_budget <= 0:
            print(f"[MssqlSource:{self.room_id}] Guvenli butce 0, retrieval atlaniyor.")
            return []

        batch_size = getattr(self.config, "fetch_batch_size", None) or self.DEFAULT_BATCH_SIZE
        max_rows = getattr(self.config, "max_rows", None) or self.DEFAULT_MAX_ROWS

        select_cols = ", ".join([ts_col] + text_cols)
        sql = (
            f"SELECT {select_cols} FROM {table} "
            f"ORDER BY {ts_col} DESC "
            f"OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        )

        try:
            conn = self._connect()
        except Exception as e:
            print(f"[MssqlSource:{self.room_id}] Baglanti hatasi: {e}")
            return []

        candidates: List[Dict[str, Any]] = []
        used_chars = 0
        offset = 0
        attempts = 0
        row_counter = 0

        try:
            cursor = conn.cursor()
            # Bütçe dolana / max_rows'a ulaşana / deneme sınırına gelene
            # kadar en yeni kayıtlardan küçük batch'ler çekilir. Eski
            # "pencereyi ikiye katla" yaklaşımı YOKTUR - offset her turda
            # sabit batch_size kadar artar ve üç sınırdan biri tetiklenince
            # kesin olarak durur (kontrolsüz büyüme/sonsuz döngü yok).
            while (
                used_chars < char_budget
                and row_counter < max_rows
                and attempts < self.MAX_FETCH_ATTEMPTS
            ):
                attempts += 1
                try:
                    cursor.execute(sql, offset, batch_size)
                    rows = cursor.fetchall()
                except Exception as e:
                    print(f"[MssqlSource:{self.room_id}] Sorgu hatasi: {e}")
                    break

                if not rows:
                    break

                for row in rows:
                    if used_chars >= char_budget or row_counter >= max_rows:
                        break
                    ts_value = row[0]
                    text_values = row[1:]
                    content = " | ".join(str(v) for v in text_values if v is not None)
                    if not content.strip():
                        continue

                    remaining = char_budget - used_chars
                    if len(content) > remaining:
                        content = content[:remaining]

                    row_counter += 1
                    used_chars += len(content)
                    candidates.append({
                        "doc_id": f"mssql_{self.notebook_id}_{offset}_{row_counter}",
                        "content": content,
                        "page": -1,
                        "score": 1.0,
                        "source": "mssql",
                        "timestamp": (
                            ts_value.isoformat() if isinstance(ts_value, datetime) else str(ts_value)
                        ),
                    })

                offset += batch_size
        except Exception as e:
            print(f"[MssqlSource:{self.room_id}] Retrieval hatasi: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

        if not candidates:
            print(f"[MssqlSource:{self.room_id}] Ilgili kayit bulunamadi.")
            return []

        print(
            f"[MssqlSource:{self.room_id}] {len(candidates)} aday, "
            f"{used_chars}/{char_budget} karakter kullanildi "
            f"(butce={budget_tokens} token)."
        )
        return candidates[:k] if k else candidates

    def to_dict(self):
        return {"id": self.room_id, "name": self.display_name}
