# =============================================================
# NEKOVA Phase 8 Tests — JSON, Env, UUID, Crypto
# =============================================================
import sys
import os
import re
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter


def run(code: str) -> list:
    """Run NEKOVA source and return list of non-empty output lines."""
    tokens = Lexer(code).tokenize()
    ast    = Parser(tokens).parse()
    interp = Interpreter()
    buf    = StringIO()
    sys.stdout = buf
    try:
        interp.execute(ast)
    finally:
        sys.stdout = sys.__stdout__
    text = re.sub(r'\x1b\[[0-9;]*m', '', buf.getvalue())
    return [l for l in text.splitlines() if l.strip()]


def run1(code: str) -> str:
    """Run and return the last output line."""
    lines = run(code)
    return lines[-1] if lines else ""


# ==============================================================
# SECTION 1 — JSON Module (use json)
# ==============================================================

class TestJSONEncode:

    def test_encode_string(self):
        out = run1('use json\nshow json_encode("hello")')
        assert out == '"hello"'

    def test_encode_number(self):
        out = run1('use json\nshow json_encode(42)')
        assert out == '42'

    def test_encode_dict(self):
        import json
        out = run1('use json\nlet d = {"name": "Emmanuel"}\nshow json_encode(d)')
        assert json.loads(out) == {"name": "Emmanuel"}

    def test_encode_list(self):
        import json
        out = run1('use json\nshow json_encode([1, 2, 3])')
        assert json.loads(out) == [1, 2, 3]

    def test_encode_boolean(self):
        out = run1('use json\nshow json_encode(true)')
        assert out == 'true'

    def test_encode_null(self):
        out = run1('use json\nshow json_encode(null)')
        assert out == 'null'

    def test_encode_nested(self):
        import json
        out = run1('use json\nlet d = {"user": {"name": "Alice", "age": 30}}\nshow json_encode(d)')
        parsed = json.loads(out)
        assert parsed["user"]["name"] == "Alice"
        assert parsed["user"]["age"] == 30


class TestJSONDecode:

    def test_decode_string(self):
        out = run1('use json\nshow json_decode("\\"hello\\"")')
        assert out == 'hello'

    def test_decode_number(self):
        out = run1('use json\nlet v = json_decode("42")\nshow v')
        assert out == '42'

    def test_decode_dict_access(self):
        out = run1('use json\nlet d = json_decode("{\\"x\\": 99}")\nshow d["x"]')
        assert out == '99'

    def test_decode_list_access(self):
        out = run1('use json\nlet arr = json_decode("[10, 20, 30]")\nshow arr[1]')
        assert out == '20'

    def test_decode_boolean(self):
        out = run1('use json\nlet v = json_decode("true")\nshow v')
        assert out == 'true'

    def test_roundtrip(self):
        import json
        code = (
            'use json\n'
            'let original = {"name": "Emmanuel", "score": 100}\n'
            'let encoded = json_encode(original)\n'
            'let decoded = json_decode(encoded)\n'
            'show decoded["name"]'
        )
        out = run1(code)
        assert out == 'Emmanuel'


class TestJSONUtilities:

    def test_json_valid_true(self):
        out = run1('use json\nshow json_valid("{\\"ok\\": true}")')
        assert out == 'true'

    def test_json_valid_false(self):
        out = run1('use json\nshow json_valid("not json")')
        assert out == 'false'

    def test_json_pretty_indented(self):
        lines = run('use json\nlet p = json_pretty({"a": 1})\nshow p')
        combined = ' '.join(lines)
        assert '"a"' in combined
        assert '1' in combined

    def test_json_get(self):
        out = run1('use json\nlet d = json_decode("{\\"name\\": \\"Alice\\"}")\nshow json_get(d, "name")')
        assert out == 'Alice'

    def test_json_get_default(self):
        out = run1('use json\nlet d = json_decode("{}")\nshow json_get(d, "missing", "default")')
        assert out == 'default'

    def test_json_keys(self):
        code = (
            'use json\n'
            'let d = json_decode("{\\"a\\": 1, \\"b\\": 2}")\n'
            'let k = json_keys(d)\n'
            'show k[0]'
        )
        out = run1(code)
        assert out in ('a', 'b')

    def test_json_merge(self):
        import json
        code = (
            'use json\n'
            'let a = {"x": 1}\n'
            'let b = {"y": 2}\n'
            'let c = json_merge(a, b)\n'
            'show json_encode(c)'
        )
        out = run1(code)
        parsed = json.loads(out)
        assert parsed == {"x": 1, "y": 2}


# ==============================================================
# SECTION 2 — Env Module (use env)
# ==============================================================

class TestEnvGetSet:

    def test_env_set_and_get(self):
        out = run1('use env\nenv_set("NEKOVA_TEST_VAR", "hello")\nshow env_get("NEKOVA_TEST_VAR")')
        assert out == 'hello'

    def test_env_get_default(self):
        out = run1('use env\nshow env_get("NEKOVA_MISSING_XYZ", "fallback")')
        assert out == 'fallback'

    def test_env_get_empty_default(self):
        out = run1('use env\nshow env_get("NEKOVA_MISSING_XYZ")')
        assert out == ''

    def test_env_has_true(self):
        out = run1('use env\nenv_set("NEKOVA_EXISTS", "yes")\nshow env_has("NEKOVA_EXISTS")')
        assert out == 'true'

    def test_env_has_false(self):
        out = run1('use env\nshow env_has("NEKOVA_DEFINITELY_NOT_SET_XYZ")')
        assert out == 'false'

    def test_env_delete(self):
        code = (
            'use env\n'
            'env_set("NEKOVA_DEL_ME", "bye")\n'
            'env_delete("NEKOVA_DEL_ME")\n'
            'show env_has("NEKOVA_DEL_ME")'
        )
        out = run1(code)
        assert out == 'false'

    def test_env_all_returns_dict(self):
        code = (
            'use env\n'
            'env_set("NEKOVA_ALLTEST", "1")\n'
            'let all = env_all()\n'
            'show all["NEKOVA_ALLTEST"]'
        )
        out = run1(code)
        assert out == '1'

    def test_env_set_overwrite(self):
        code = (
            'use env\n'
            'env_set("NEKOVA_OVER", "first")\n'
            'env_set("NEKOVA_OVER", "second")\n'
            'show env_get("NEKOVA_OVER")'
        )
        out = run1(code)
        assert out == 'second'

    def test_env_load_dotenv(self, tmp_path):
        """env_load() reads a .env file into the environment."""
        env_file = tmp_path / ".env"
        env_file.write_text('NEKOVA_LOADED=from_file\nNEKOVA_PORT=9090\n')
        path = str(env_file).replace('\\', '/')
        code = (
            f'use env\n'
            f'env_load("{path}")\n'
            f'show env_get("NEKOVA_LOADED")'
        )
        out = run1(code)
        assert out == 'from_file'

    def test_env_require_present(self):
        code = (
            'use env\n'
            'env_set("NEKOVA_REQUIRED", "value")\n'
            'show env_require("NEKOVA_REQUIRED")'
        )
        out = run1(code)
        assert out == 'value'

    def test_env_fstring_usage(self):
        code = (
            'use env\n'
            'env_set("APP_NAME", "NEKOVA")\n'
            'let name = env_get("APP_NAME")\n'
            'show f"Welcome to {name}"'
        )
        out = run1(code)
        assert out == 'Welcome to NEKOVA'


# ==============================================================
# SECTION 3 — UUID Module (use uuid)
# ==============================================================

class TestUUIDGeneration:

    def test_uuid_format(self):
        import re
        out = run1('use uuid\nshow uuid()')
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        assert re.match(pattern, out), f"Not a valid UUID v4: {out}"

    def test_uuid4_format(self):
        import re
        out = run1('use uuid\nshow uuid4()')
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        assert re.match(pattern, out)

    def test_uuid_unique(self):
        code = 'use uuid\nlet a = uuid()\nlet b = uuid()\nshow a\nshow b'
        lines = run(code)
        assert len(lines) == 2
        assert lines[0] != lines[1]

    def test_uuid5_deterministic(self):
        code = (
            'use uuid\n'
            'let a = uuid5("nekova")\n'
            'let b = uuid5("nekova")\n'
            'show a\nshow b'
        )
        lines = run(code)
        assert lines[0] == lines[1]

    def test_uuid5_different_names(self):
        code = (
            'use uuid\n'
            'let a = uuid5("nekova")\n'
            'let b = uuid5("aion")\n'
            'show a\nshow b'
        )
        lines = run(code)
        assert lines[0] != lines[1]


class TestUUIDValidation:

    def test_uuid_valid_true(self):
        out = run1('use uuid\nlet id = uuid()\nshow uuid_valid(id)')
        assert out == 'true'

    def test_uuid_valid_false_random(self):
        out = run1('use uuid\nshow uuid_valid("not-a-uuid")')
        assert out == 'false'

    def test_uuid_valid_false_empty(self):
        out = run1('use uuid\nshow uuid_valid("")')
        assert out == 'false'

    def test_uuid_short_length(self):
        out = run1('use uuid\nlet s = uuid_short(8)\nshow s')
        assert len(out) == 8

    def test_uuid_short_default(self):
        out = run1('use uuid\nshow uuid_short()')
        assert len(out) == 8

    def test_uuid_short_alphanumeric(self):
        import re
        out = run1('use uuid\nshow uuid_short(12)')
        assert re.match(r'^[0-9a-f]+$', out)
        assert len(out) == 12

    def test_uuid_nano_length(self):
        out = run1('use uuid\nshow uuid_nano()')
        assert len(out) == 12

    def test_uuid_parts(self):
        code = (
            'use uuid\n'
            'let id = uuid()\n'
            'let parts = uuid_parts(id)\n'
            'show parts["version"]'
        )
        out = run1(code)
        assert out == '4'


# ==============================================================
# SECTION 4 — Crypto Module (use crypto)
# ==============================================================

class TestCryptoHashing:

    def test_sha256_known(self):
        # echo -n "hello" | sha256sum
        out = run1('use crypto\nshow sha256("hello")')
        assert out == '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'

    def test_sha256_via_hash(self):
        out = run1('use crypto\nshow hash("hello")')
        assert out == '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'

    def test_sha512_known(self):
        import hashlib
        expected = hashlib.sha512(b"hello").hexdigest()
        out = run1('use crypto\nshow sha512("hello")')
        assert out == expected

    def test_md5_known(self):
        import hashlib
        expected = hashlib.md5(b"hello").hexdigest()
        out = run1('use crypto\nshow md5("hello")')
        assert out == expected

    def test_sha1_known(self):
        import hashlib
        expected = hashlib.sha1(b"hello").hexdigest()
        out = run1('use crypto\nshow sha1("hello")')
        assert out == expected

    def test_hash_algorithm_param(self):
        import hashlib
        expected = hashlib.sha512(b"test").hexdigest()
        out = run1('use crypto\nshow hash("test", "sha512")')
        assert out == expected

    def test_hash_empty_string(self):
        import hashlib
        expected = hashlib.sha256(b"").hexdigest()
        out = run1('use crypto\nshow sha256("")')
        assert out == expected

    def test_hash_deterministic(self):
        code = (
            'use crypto\n'
            'let a = sha256("nekova")\n'
            'let b = sha256("nekova")\n'
            'show a\nshow b'
        )
        lines = run(code)
        assert lines[0] == lines[1]

    def test_hash_different_inputs(self):
        code = (
            'use crypto\n'
            'let a = sha256("hello")\n'
            'let b = sha256("world")\n'
            'show a\nshow b'
        )
        lines = run(code)
        assert lines[0] != lines[1]

    def test_hash_returns_hex(self):
        import re
        out = run1('use crypto\nshow sha256("test")')
        assert re.match(r'^[0-9a-f]+$', out)
        assert len(out) == 64


class TestCryptoPassword:

    def test_hash_password_returns_string(self):
        out = run1('use crypto\nshow hash_password("secret")')
        assert out.startswith('pbkdf2$')

    def test_check_password_correct(self):
        code = (
            'use crypto\n'
            'let h = hash_password("mypassword")\n'
            'show check_password("mypassword", h)'
        )
        out = run1(code)
        assert out == 'true'

    def test_check_password_wrong(self):
        code = (
            'use crypto\n'
            'let h = hash_password("mypassword")\n'
            'show check_password("wrongpassword", h)'
        )
        out = run1(code)
        assert out == 'false'

    def test_hash_password_unique_salts(self):
        code = (
            'use crypto\n'
            'let h1 = hash_password("same")\n'
            'let h2 = hash_password("same")\n'
            'show h1\nshow h2'
        )
        lines = run(code)
        # Same password should produce different hashes (different salts)
        assert lines[0] != lines[1]

    def test_hash_password_both_verify(self):
        code = (
            'use crypto\n'
            'let h1 = hash_password("password")\n'
            'let h2 = hash_password("password")\n'
            'show check_password("password", h1)\n'
            'show check_password("password", h2)'
        )
        lines = run(code)
        assert lines[0] == 'true'
        assert lines[1] == 'true'

    def test_check_password_empty_wrong(self):
        code = (
            'use crypto\n'
            'let h = hash_password("secret")\n'
            'show check_password("", h)'
        )
        out = run1(code)
        assert out == 'false'


class TestCryptoTokens:

    def test_token_length(self):
        out = run1('use crypto\nshow token(16)')
        # token(16) produces 16 bytes = 32 hex chars
        assert len(out) == 32

    def test_token_default_length(self):
        out = run1('use crypto\nshow token()')
        # token(32) = 64 hex chars
        assert len(out) == 64

    def test_token_hex_chars(self):
        import re
        out = run1('use crypto\nshow token(8)')
        assert re.match(r'^[0-9a-f]+$', out)

    def test_token_unique(self):
        code = 'use crypto\nlet a = token(16)\nlet b = token(16)\nshow a\nshow b'
        lines = run(code)
        assert lines[0] != lines[1]

    def test_token_url_safe(self):
        import re
        out = run1('use crypto\nshow token_url(16)')
        # URL-safe: no +, /, or = in output
        assert re.match(r'^[A-Za-z0-9_\-]+$', out)


class TestCryptoBase64:

    def test_encode_b64(self):
        out = run1('use crypto\nshow encode_b64("hello")')
        assert out == 'aGVsbG8='

    def test_decode_b64(self):
        out = run1('use crypto\nshow decode_b64("aGVsbG8=")')
        assert out == 'hello'

    def test_b64_roundtrip(self):
        code = (
            'use crypto\n'
            'let original = "Hello, NEKOVA!"\n'
            'let encoded = encode_b64(original)\n'
            'let decoded = decode_b64(encoded)\n'
            'show decoded'
        )
        out = run1(code)
        assert out == 'Hello, NEKOVA!'

    def test_encode_b64_url(self):
        import re
        out = run1('use crypto\nshow encode_b64_url("hello world")')
        # URL-safe: no + or /
        assert '+' not in out and '/' not in out

    def test_decode_b64_url(self):
        code = (
            'use crypto\n'
            'let e = encode_b64_url("hello world")\n'
            'show decode_b64_url(e)'
        )
        out = run1(code)
        assert out == 'hello world'

    def test_b64_empty_string(self):
        out = run1('use crypto\nshow encode_b64("")')
        assert out == ''

    def test_b64_unicode(self):
        code = (
            'use crypto\n'
            'let e = encode_b64("NEKOVA")\n'
            'show decode_b64(e)'
        )
        out = run1(code)
        assert out == 'NEKOVA'


class TestCryptoHMAC:

    def test_hmac_returns_hex(self):
        import re
        out = run1('use crypto\nshow hmac("message", "key")')
        assert re.match(r'^[0-9a-f]{64}$', out)

    def test_hmac_deterministic(self):
        code = (
            'use crypto\n'
            'let a = hmac("msg", "key")\n'
            'let b = hmac("msg", "key")\n'
            'show a\nshow b'
        )
        lines = run(code)
        assert lines[0] == lines[1]

    def test_hmac_different_keys(self):
        code = (
            'use crypto\n'
            'let a = hmac("msg", "key1")\n'
            'let b = hmac("msg", "key2")\n'
            'show a\nshow b'
        )
        lines = run(code)
        assert lines[0] != lines[1]

    def test_hmac_valid_true(self):
        code = (
            'use crypto\n'
            'let sig = hmac("message", "secret")\n'
            'show hmac_valid("message", "secret", sig)'
        )
        out = run1(code)
        assert out == 'true'

    def test_hmac_valid_false(self):
        code = (
            'use crypto\n'
            'let sig = hmac("message", "secret")\n'
            'show hmac_valid("message", "wrongkey", sig)'
        )
        out = run1(code)
        assert out == 'false'


# ==============================================================
# SECTION 5 — Integration tests
# ==============================================================

class TestPhase8Integration:

    def test_json_with_uuid_key(self):
        code = (
            'use json\n'
            'use uuid\n'
            'let id = uuid_short(8)\n'
            'let data = json_encode({"id": id, "name": "Emmanuel"})\n'
            'show json_valid(data)'
        )
        out = run1(code)
        assert out == 'true'

    def test_env_with_json(self):
        code = (
            'use env\n'
            'use json\n'
            'env_set("CONFIG", "{\\"debug\\": true}")\n'
            'let raw = env_get("CONFIG")\n'
            'let cfg = json_decode(raw)\n'
            'show cfg["debug"]'
        )
        out = run1(code)
        assert out == 'true'

    def test_crypto_token_as_uuid_like(self):
        code = (
            'use crypto\n'
            'let tok = token(16)\n'
            'show tok'
        )
        out = run1(code)
        assert len(out) == 32

    def test_json_encode_decode_list(self):
        code = (
            'use json\n'
            'let items = [1, 2, 3, 4, 5]\n'
            'let encoded = json_encode(items)\n'
            'let decoded = json_decode(encoded)\n'
            'show decoded[2]'
        )
        out = run1(code)
        assert out == '3'

    def test_hash_password_in_task(self):
        code = (
            'use crypto\n'
            'task register(password):\n'
            '    let h = hash_password(password)\n'
            '    return h\n'
            'task login(password, stored):\n'
            '    return check_password(password, stored)\n'
            'let stored = register("mypass")\n'
            'show login("mypass", stored)\n'
            'show login("wrong", stored)'
        )
        lines = run(code)
        assert lines[-2] == 'true'
        assert lines[-1] == 'false'

    def test_uuid_with_match(self):
        code = (
            'use uuid\n'
            'let id = uuid()\n'
            'let valid = uuid_valid(id)\n'
            'match valid:\n'
            '    when true: show "valid uuid"\n'
            '    when false: show "invalid uuid"'
        )
        out = run1(code)
        assert out == 'valid uuid'

    def test_json_with_db(self):
        code = (
            'use json\n'
            'let db = connect(":memory:")\n'
            'db.create("config", {"key": "text", "value": "text"})\n'
            'let payload = json_encode({"port": 8080})\n'
            'db.insert("config", {"key": "server", "value": payload})\n'
            'let row = db.query("config").first()\n'
            'let cfg = json_decode(row.value)\n'
            'show cfg["port"]'
        )
        out = run1(code)
        assert out == '8080'

    def test_all_four_modules_load(self):
        code = (
            'use json\n'
            'use env\n'
            'use uuid\n'
            'use crypto\n'
            'show "all loaded"'
        )
        out = run1(code)
        assert out == 'all loaded'