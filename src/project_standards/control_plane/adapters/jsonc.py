"""Compose JSON-family semantic units without reserializing consumer files.

``json.loads`` validates a copy whose JSONC comments and trailing commas are
replaced by spaces. The replacement keeps character offsets aligned with a
small lexical tree, allowing mutations to splice only the selected value and
the minimum required separator while retaining all other source bytes.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
import zlib
from base64 import b85decode
from bisect import bisect_right
from dataclasses import dataclass
from typing import Literal, cast
from urllib.parse import unquote

from project_standards.control_plane.adapters.base import (
    AdapterState,
    AdapterUnit,
    UnitChange,
    apply_edits,
    decode_json_pointer,
    decode_utf8,
    line_start,
    preferred_newline,
)
from project_standards.control_plane.codec import semantic_digest
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.package_contract.payload import (
    AdapterKind,
    JsonValue,
    normalize_scope,
)

_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_MISSING = object()
_PRETTIER_PRINT_WIDTH = 88


def _range_bounds(spec: str) -> tuple[int, ...]:
    bounds: list[int] = []
    for raw_interval in spec.split(","):
        raw_start, separator, raw_stop = raw_interval.partition("-")
        start = int(raw_start, 16)
        stop = int(raw_stop, 16) + 1 if separator else start + 1
        bounds.extend((start, stop))
    return tuple(bounds)


# These generated constants pin Prettier 3.8.3's East Asian width lookup and
# emoji-regex 10.6.0 semantics without adding formatter runtime dependencies.
_PRETTIER_DOUBLE_WIDTH_BOUNDS = _range_bounds(
    "1100-115f,231a-231b,2329-232a,23e9-23ec,23f0,23f3,25fd-25fe,2614-2615,2630-2637,2648-2"
    "653,267f,268a-268f,2693,26a1,26aa-26ab,26bd-26be,26c4-26c5,26ce,26d4,26ea,26f2-26f3,26"
    "f5,26fa,26fd,2705,270a-270b,2728,274c,274e,2753-2755,2757,2795-2797,27b0,27bf,2b1b-2b1"
    "c,2b50,2b55,2e80-2e99,2e9b-2ef3,2f00-2fd5,2ff0-303e,3041-3096,3099-30ff,3105-312f,3131"
    "-318e,3190-31e5,31ef-321e,3220-3247,3250-a48c,a490-a4c6,a960-a97c,ac00-d7a3,f900-faff,"
    "fe10-fe19,fe30-fe52,fe54-fe66,fe68-fe6b,ff01-ff60,ffe0-ffe6,16fe0-16fe4,16ff0-16ff6,17"
    "000-18cd5,18cff-18d1e,18d80-18df2,1aff0-1aff3,1aff5-1affb,1affd-1affe,1b000-1b122,1b13"
    "2,1b150-1b152,1b155,1b164-1b167,1b170-1b2fb,1d300-1d356,1d360-1d376,1f004,1f0cf,1f18e,"
    "1f191-1f19a,1f200-1f202,1f210-1f23b,1f240-1f248,1f250-1f251,1f260-1f265,1f300-1f320,1f"
    "32d-1f335,1f337-1f37c,1f37e-1f393,1f3a0-1f3ca,1f3cf-1f3d3,1f3e0-1f3f0,1f3f4,1f3f8-1f43"
    "e,1f440,1f442-1f4fc,1f4ff-1f53d,1f54b-1f54e,1f550-1f567,1f57a,1f595-1f596,1f5a4,1f5fb-"
    "1f64f,1f680-1f6c5,1f6cc,1f6d0-1f6d2,1f6d5-1f6d8,1f6dc-1f6df,1f6eb-1f6ec,1f6f4-1f6fc,1f"
    "7e0-1f7eb,1f7f0,1f90c-1f93a,1f93c-1f945,1f947-1f9ff,1fa70-1fa7c,1fa80-1fa8a,1fa8e-1fac"
    "6,1fac8,1facd-1fadc,1fadf-1faea,1faef-1faf8,20000-2fffd,30000-3fffd"
)
_PRETTIER_EMOJI_PATTERN_SHA256 = "be213f75d7b014abceaffc0e69aa362b426c387fb6213394c6940e116ff226be"
_PRETTIER_EMOJI_PATTERN = re.compile(
    zlib.decompress(
        b85decode(
            "c-rlo-ICiZ5{55kPu5%IDoIEnzLS*ryNSe?k*YoL#V<T9d5~n!II%rDoBa;*dJxbw{WeV_l<)ueS97$dA3sxU("
            "zhQ!yC$mh_aFbBZ2lKZS^0v!&DeHbLB-#;Kk`Fi5}Y!sR?rpf#)3W-jN!-+h17x_I8u>HzuuQe1CoZR$QYb1=$"
            "nFxC&`0FJ>4`%etM8cZ42_G9l)Z7?i#QI6{x`pq;FTW(+Z8WqN1l;Pq$tw26_*))l_SqXhzdW)r@Hzh-^c9iy*"
            "O{wg$8yO>LQ*o)9`wi!HR{iDPOmfC%+W(=!-$)`2z=nMtgZ&?_M>(G+8wrUOUNf<=UBd5#55tHCm)>56Eh6i96"
            "^SR|VP#1dvIEiG-VDx<q*IPy~(IlRNQWv*_>)v8eqn1@kau}a2^TV{tWB%(s&!EpNLx4(Y;45RY7GNj~={G`)a"
            "Ivu2!X=I}AX8XCJidNjy<BJWb@H4D!A(&}t{8D?2>R}<kLWHR#dJY&2)As1xM~tM7{7`MNiNOmD3>%lQNmJ&L<"
            "*L~PXx}wWU=9WSG-TBo(0*u(OZV@!M=$mjIY#%}!4|n?ywDA23V9kK8hfBu88o*l<NC4&Lof~4f)PxmNAa}~l_"
            "{zfKg!snXXgtlUC@+~lI3qpQ)_8d7DvVi7J13j)bk{Wq(DV+_Kc?Xo{&bKmgthveBceaNe@o%H2lz}A_&F3KRw"
            "P7MlNeSgb~Bq_Q=nKeTz+F%ikRqSKW~x4USTverP~gAb@5T8Zb~$7)u!ny#fa*OrWP=V9rDeBNiLA&_$m~M0>{"
            "ZLIBj3aFx-5Nw}j&lpYCX*cTQXg%I_d{X(QJl+~IMYb0E*Y$+LW#e_1U#JY?$O}O$!q^U*f%cDRr$UjL0ANMjX"
            "=qkx^C3)OS9z`<fj+Nq#h%}<?aV5vra;9p|qFS??^U`s;r9dr2tYKy|%{^V+Gahe@W9HWW0~5yDgbEz?w8U9js"
            "HCk1Rh5bCO5J$HEvDPN&ArmjuB+J%(hL>0=C9{fD>qasUU3Qh^UYGnijr7OcP7KtW?`5una7I3X5}>KbDjHJtE"
            "S)0U|LD+MWQHkzBJwpGF{P0)w8mD%9DN*9rgL5!G;`BaI76??mu2JYt7W+ulscy)>gB3E!iOMvl4wHA}oThEJe"
            "Tbp7DyuxO>)ctc1*KBCQsss5H)1p<=Q*Uk2TndtN3f?KGH`7VD?J-)AN%I>`-E@2=I_xz?*YHdje5_WNNaShCG"
            "JlX)x8LnU=JwUHECvV@CSQZrt<)w7cW#HFz-8U?RS^>-(K%d~ts4P2^X-KF&RMpcihzfCXIwP0UWt3y@DdBZ_e"
            "4@(-R3TIw6x*n%w(+)aS=^5@~WVIL?jd<}WOL(OBL_C;qIY*puknivwPkIr^ltPeL%PyXuNdeD{bd0L<-c);R$"
            "wWw!qGvruGMp%xK#T)eG>inunA9q<^W|WcQGraz4`MWZ;m2!S%WD#6(}|gRWN2kZu*}Pkh$3I~Bet|H`8HNGpv"
            "5xesj+1D8PVFK;yc;ilE&#Mqqi4N5W@Y)lMxk1bc2{E`B&_vfW7(vl8;YCM07nkJesuz1F5#T@068Of7tR3Q)t"
            "-veK|g66iPbG*%5?2NvKy|3K8a@tfxy)+o3&P7LnKVFe12|sWaj&exxJGryoaoghWe)#Yug6Kao+qfavIxgm5|"
            "A^b*{$Wf)}V!gInTA)fl!1<9@@mG0$0BfOA(<Asq~#9k6^)?OUNn<vgd6P_2HP$vDIxKAr90H+VqC(tJd{b2;X"
            "6l9^`3+x3kiDV|Y<kHmVjGB1uo3V~)`5Z2h&bPxlQey}=&9$B0#Le9CT%Qc*fa#T6#pS-Q<8o%Uy?LA^Hq>qPx"
            "Z49PCvL0drN!wj7*}W4TI?K$M^`^Qd=u&C%CDJjVj0edn)v|3nT7y3+cAdICfsU5hb}KGb|Y(j<=n3IGDEYe{a"
            "%NyQ;F<6arnCg-43VZ$Q*I~Xggu{;jx7Gd0JsgZ;{^3Z(FWyw={OLVw^f14sS07Bx1al#aqGYDb(I)`10mzWA&"
            "9<{t|pQCT@u)F`e%0e}0UZC8zQK_l!tH3=i_Mk@6&V!r$zOmxA#b6s<))iKqBCPoh?MkfODeC$W?MW=GVD5AqT"
            "pXJp9@wS5&S>pbjpd3Z4Gnl1B!-0@2%bbH1&q^=trzUG3nccpp1Y54Q9SZ^8SdX6ZI`(9O_n-u<mtbULxeg?PO"
            "Jo6rgw`xB(z5HW&en08_JhC?#>-~&xCh**B^-rYz{T%jF7~dqocagnO`?-1VpUZRnZ!#QziQ8D`&cO`N_{1l_x"
            "{lXABpT;hHC(H8OYJ5hg~-mW2k5(%9{DRlaM<YK^k-cCZOLw+xq<Rl?$28aN{Ho+e&BnVz->%$-19h|;E93P@y"
            "k6I@9Dj&UfR!hRPyCbzH|NH9w>B(=6jnUR|!FJ9VfRVVSW)WS8!DD-BXayfP&n;$u(XG4`2Jpja^8m`<mkjp`l"
            "YNCTwMiN`XtCAeTO&6H9Y_rsVF0i=NO+y%DnuEnH*;Cmc+&MCG;-3Imszarx?j57Oke#Q5sEWt6*@DEx4b!uLm"
            "!?~j)I#^B{LMeZA?`E<;(^YOE8sI%qn58dwsR{09+<M4WaY<)Ob3OiRqrZ`(WPk&d@UAd78-D0j=wNE{-*55x~"
            "_CQ_&U9`V>3VWQR2e!cXlskM1t2dK^^#=H^qE9)U{vwB0PFr7%$(Ni-U&rT5&Z57?>i$^uHK~2YG4$2^zT)Kht"
            "0eDFQeTeWSDZIrNbM`mnZL(s{K|aB{}m=zr^=YxOM1J{mfrraNB#A2y*=+X=UZL2JHRgfzu$2aT6TfuX77#n?t"
            "J%yj*)AWZ-@T?>w`&y"
        )
    ).decode("ascii")
)
_PRETTIER_NARROW_EMOJIS = frozenset(
    "\xa9\xae\u203c\u2049\u2122\u2139\u2194\u2195\u2196\u2197\u2198\u2199\u21a9\u21aa\u2328\u23cf\u23f1\u23f2\u23f8\u23f9\u23fa\u25aa\u25ab\u25b6\u25c0\u25fb\u25fc\u2600\u2601\u2602\u2603\u2604\u260e\u2611\u2618\u261d\u2620\u2622\u2623\u2626\u262a\u262e\u262f\u2638\u2639\u263a\u2640\u2642\u265f\u2660\u2663\u2665\u2666\u2668\u267b\u267e\u2692\u2694\u2695\u2696\u2697\u2699\u269b\u269c\u26a0\u26a7\u26b0\u26b1\u26c8\u26cf\u26d1\u26d3\u26e9\u26f1\u26f7\u26f8\u26f9\u2702\u2708\u2709\u270c\u270d\u270f\u2712\u2714\u2716\u271d\u2721\u2733\u2734\u2744\u2747\u2763\u2764\u27a1\u2934\u2935\u2b05\u2b06\u2b07"
)

type TokenKind = Literal[
    "string",
    "number",
    "true",
    "false",
    "null",
    "open-object",
    "close-object",
    "open-array",
    "close-array",
    "colon",
    "comma",
    "whitespace",
    "comment",
]
type NodeKind = Literal["object", "array", "scalar"]
type ScopeKind = Literal["key", "set", "keyed-set"]


@dataclass(frozen=True, slots=True)
class JsonToken:
    """One lexical token with absolute character offsets."""

    kind: TokenKind
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class JsonMember:
    """One object member and the comma that follows it, when present."""

    key: str
    key_token: JsonToken
    value: JsonNode
    comma: JsonToken | None


@dataclass(frozen=True, slots=True)
class JsonNode:
    """One semantic JSON value with exact lexical boundaries."""

    kind: NodeKind
    start: int
    end: int
    value: JsonValue
    opening: JsonToken | None = None
    closing: JsonToken | None = None
    members: tuple[JsonMember, ...] = ()
    elements: tuple[JsonNode, ...] = ()
    commas: tuple[JsonToken | None, ...] = ()


@dataclass(frozen=True, slots=True)
class JsonDocument:
    """Parsed semantics plus source-preserving lexical structure."""

    text: str
    root: JsonNode


@dataclass(frozen=True, slots=True)
class ScopeSpec:
    """One normalized JSON-family selector decomposed for lookup."""

    normalized: str
    kind: ScopeKind
    path: tuple[str, ...]
    identity_key: str | None = None
    identity: str | None = None


@dataclass(frozen=True, slots=True)
class LocatedUnit:
    """A selected node plus enough parent context for bounded removal."""

    node: JsonNode
    container: JsonNode
    index: int
    member: JsonMember | None = None


@dataclass(frozen=True, slots=True)
class JsonLayout:
    """Newline and indentation inferred from the containing consumer document."""

    newline: str
    indent_unit: str


class _DuplicateObjectKey(ValueError):
    pass


def _codepoint_width(character: str) -> int:
    codepoint = ord(character)
    if (
        codepoint <= 31
        or 127 <= codepoint <= 159
        or 768 <= codepoint <= 879
        or 65024 <= codepoint <= 65039
    ):
        return 0
    return 2 if bisect_right(_PRETTIER_DOUBLE_WIDTH_BOUNDS, codepoint) % 2 == 1 else 1


def _utf16_units(value: str) -> str:
    encoded = value.encode("utf-16-le", errors="surrogatepass")
    return "".join(
        chr(encoded[index] | encoded[index + 1] << 8) for index in range(0, len(encoded), 2)
    )


def _decode_utf16_units(value: str) -> str:
    encoded = b"".join(ord(character).to_bytes(2, "little") for character in value)
    return encoded.decode("utf-16-le", errors="surrogatepass")


def _emoji_width_replacement(match: re.Match[str]) -> str:
    return " " if match.group() in _PRETTIER_NARROW_EMOJIS else "  "


def _prettier_width(value: str) -> int:
    """Mirror pinned Prettier display width without a formatter dependency."""
    if value.isascii() and all(0x20 <= ord(character) <= 0x7F for character in value):
        return len(value)
    utf16 = _utf16_units(value)
    replaced = _PRETTIER_EMOJI_PATTERN.sub(_emoji_width_replacement, utf16)
    return sum(_codepoint_width(character) for character in _decode_utf16_units(replaced))


def _fits_prettier_line(indent: str, prefix_width: int, flat: str) -> bool:
    return len(indent.expandtabs(2)) + prefix_width + _prettier_width(flat) <= _PRETTIER_PRINT_WIDTH


def _prettier_number(token: str) -> str:
    """Normalize JSON number spelling without a lossy numeric conversion."""
    mantissa, separator, exponent = token.lower().partition("e")
    if "." in mantissa:
        whole, fraction = mantissa.split(".", 1)
        mantissa = f"{whole}.{fraction.rstrip('0') or '0'}"
    if not separator:
        return mantissa
    negative = exponent.startswith("-")
    digits = exponent.lstrip("+-").lstrip("0") or "0"
    if digits == "0":
        return mantissa
    sign = "-" if negative else ""
    return f"{mantissa}e{sign}{digits}"


def _flat_json(value: JsonValue) -> str:
    if isinstance(value, dict):
        if not value:
            return "{}"
        members = (
            f"{json.dumps(key, ensure_ascii=True)}: {_flat_json(item)}"
            for key, item in value.items()
        )
        return f"{{ {', '.join(members)} }}"
    if isinstance(value, list):
        return f"[{', '.join(_flat_json(item) for item in value)}]"
    return json.dumps(value, ensure_ascii=True, allow_nan=False)


def _forces_prettier_break(value: JsonValue) -> bool:
    if isinstance(value, list):
        homogeneous_table = len(value) > 1 and all(
            isinstance(item, dict) and len(item) > 1 for item in value
        )
        homogeneous_matrix = len(value) > 1 and all(
            isinstance(item, list) and len(item) > 1 for item in value
        )
        return (
            homogeneous_table
            or homogeneous_matrix
            or any(_forces_prettier_break(item) for item in value)
        )
    if isinstance(value, dict):
        return any(_forces_prettier_break(item) for item in value.values())
    return False


def _prettier_json(
    value: JsonValue,
    indent: str = "",
    *,
    force_break: bool = False,
    prefix_width: int = 0,
    indent_unit: str = "\t",
    newline: str = "\n",
) -> str:
    flat = _flat_json(value)
    if (
        not force_break
        and not _forces_prettier_break(value)
        and _fits_prettier_line(indent, prefix_width, flat)
    ):
        return flat
    child_indent = f"{indent}{indent_unit}"
    if isinstance(value, dict):
        members: list[str] = []
        for index, (key, item) in enumerate(value.items()):
            rendered_key = json.dumps(key, ensure_ascii=True)
            rendered_value = _prettier_json(
                item,
                child_indent,
                force_break=_forces_prettier_break(item),
                prefix_width=(
                    _prettier_width(rendered_key) + 2 + (1 if index < len(value) - 1 else 0)
                ),
                indent_unit=indent_unit,
                newline=newline,
            )
            members.append(f"{child_indent}{rendered_key}: {rendered_value}")
        return f"{{{newline}" + f",{newline}".join(members) + f"{newline}{indent}}}"
    if isinstance(value, list):
        items: list[str] = []
        for index, item in enumerate(value):
            rendered = _prettier_json(
                item,
                child_indent,
                prefix_width=(1 if index < len(value) - 1 else 0),
                indent_unit=indent_unit,
                newline=newline,
            )
            items.append(f"{child_indent}{rendered}")
        return f"[{newline}" + f",{newline}".join(items) + f"{newline}{indent}]"
    return flat


def format_fresh_json_container(content: bytes, kind: AdapterKind) -> bytes:
    """Format a newly materialized JSON-family container to repository style."""
    if kind not in {AdapterKind.JSON, AdapterKind.JSONC}:
        raise ControlPlaneError("fresh JSON formatting requires a JSON-family adapter")
    value = _parse(content, kind).root.value
    return f"{_prettier_json(value)}\n".encode()


def _scan_string(text: str, start: int) -> int:
    index = start + 1
    while index < len(text):
        character = text[index]
        if character == '"':
            return index + 1
        if character == "\\":
            index += 2
            continue
        if ord(character) < 0x20:
            raise ValueError("JSON string contains an unescaped control character")
        index += 1
    raise ValueError("JSON string is not terminated")


def _lex(text: str, *, allow_comments: bool) -> tuple[JsonToken, ...]:
    tokens: list[JsonToken] = []
    punctuation: dict[str, TokenKind] = {
        "{": "open-object",
        "}": "close-object",
        "[": "open-array",
        "]": "close-array",
        ":": "colon",
        ",": "comma",
    }
    literals: dict[str, TokenKind] = {
        "true": "true",
        "false": "false",
        "null": "null",
    }
    index = 0
    while index < len(text):
        character = text[index]
        if character in " \t\r\n":
            end = index + 1
            while end < len(text) and text[end] in " \t\r\n":
                end += 1
            tokens.append(JsonToken("whitespace", index, end))
            index = end
            continue
        if character == '"':
            end = _scan_string(text, index)
            json.loads(text[index:end])
            tokens.append(JsonToken("string", index, end))
            index = end
            continue
        if character in punctuation:
            tokens.append(JsonToken(punctuation[character], index, index + 1))
            index += 1
            continue
        if text.startswith("//", index) or text.startswith("/*", index):
            if not allow_comments:
                raise ValueError("comments are not valid JSON")
            if text.startswith("//", index):
                newline = text.find("\n", index + 2)
                end = len(text) if newline == -1 else newline
            else:
                closing = text.find("*/", index + 2)
                if closing == -1:
                    raise ValueError("block comment is not terminated")
                end = closing + 2
            tokens.append(JsonToken("comment", index, end))
            index = end
            continue
        literal = next((value for value in literals if text.startswith(value, index)), None)
        if literal is not None:
            end = index + len(literal)
            tokens.append(JsonToken(literals[literal], index, end))
            index = end
            continue
        match = _NUMBER.match(text, index)
        if match is not None:
            tokens.append(JsonToken("number", index, match.end()))
            index = match.end()
            continue
        raise ValueError("JSON content contains an unexpected token")
    return tuple(tokens)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateObjectKey("duplicate object key")
        result[key] = value
    return result


def _reject_constant(_: str) -> object:
    raise ValueError("JSON number is not finite")


def _semantic_view(
    text: str,
    tokens: tuple[JsonToken, ...],
    *,
    allow_extensions: bool,
) -> JsonValue:
    cleaned = list(text)
    significant = [token for token in tokens if token.kind not in {"whitespace", "comment"}]
    for token in tokens:
        if token.kind != "comment":
            continue
        for index in range(token.start, token.end):
            if cleaned[index] not in "\r\n":
                cleaned[index] = " "
    if allow_extensions:
        for index, token in enumerate(significant[:-1]):
            if token.kind == "comma" and significant[index + 1].kind in {
                "close-array",
                "close-object",
            }:
                cleaned[token.start] = " "
    try:
        parsed = json.loads(
            "".join(cleaned),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except _DuplicateObjectKey:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("semantic JSON parsing failed") from exc
    return _json_value(parsed)


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("JSON number is not finite")
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in cast("list[object]", value)]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in cast("dict[str, object]", value).items()}
    raise ValueError("value is not JSON-compatible")


class _StructureParser:
    """Derive source spans from tokens after json.loads validates semantics."""

    def __init__(self, text: str, tokens: tuple[JsonToken, ...]) -> None:
        self._text = text
        self._tokens = tuple(
            token for token in tokens if token.kind not in {"whitespace", "comment"}
        )
        self._index = 0

    def parse(self) -> JsonNode:
        node = self._value()
        if self._index != len(self._tokens):
            raise ValueError("JSON document contains more than one value")
        return node

    def _peek(self) -> JsonToken | None:
        return self._tokens[self._index] if self._index < len(self._tokens) else None

    def _take(self, kind: TokenKind | None = None) -> JsonToken:
        token = self._peek()
        if token is None or (kind is not None and token.kind != kind):
            raise ValueError("JSON token sequence is malformed")
        self._index += 1
        return token

    def _value(self) -> JsonNode:
        token = self._peek()
        if token is None:
            raise ValueError("JSON value is missing")
        if token.kind == "open-object":
            return self._object()
        if token.kind == "open-array":
            return self._array()
        if token.kind not in {"string", "number", "true", "false", "null"}:
            raise ValueError("JSON value token is invalid")
        self._take()
        return JsonNode(
            "scalar",
            token.start,
            token.end,
            _json_value(json.loads(self._text[token.start : token.end])),
        )

    def _object(self) -> JsonNode:
        opening = self._take("open-object")
        members: list[JsonMember] = []
        value: dict[str, JsonValue] = {}
        while (token := self._peek()) is not None and token.kind != "close-object":
            key_token = self._take("string")
            key = cast("str", json.loads(self._text[key_token.start : key_token.end]))
            self._take("colon")
            child = self._value()
            comma = self._take("comma") if self._peek_kind() == "comma" else None
            members.append(JsonMember(key, key_token, child, comma))
            value[key] = child.value
            if comma is None and self._peek_kind() != "close-object":
                raise ValueError("JSON object members require a comma")
        closing = self._take("close-object")
        return JsonNode(
            "object",
            opening.start,
            closing.end,
            value,
            opening,
            closing,
            tuple(members),
        )

    def _array(self) -> JsonNode:
        opening = self._take("open-array")
        elements: list[JsonNode] = []
        commas: list[JsonToken | None] = []
        while (token := self._peek()) is not None and token.kind != "close-array":
            elements.append(self._value())
            comma = self._take("comma") if self._peek_kind() == "comma" else None
            commas.append(comma)
            if comma is None and self._peek_kind() != "close-array":
                raise ValueError("JSON array elements require a comma")
        closing = self._take("close-array")
        return JsonNode(
            "array",
            opening.start,
            closing.end,
            [element.value for element in elements],
            opening,
            closing,
            elements=tuple(elements),
            commas=tuple(commas),
        )

    def _peek_kind(self) -> TokenKind | None:
        token = self._peek()
        return token.kind if token is not None else None


def _parse(content: bytes, kind: AdapterKind, *, fragment: bool = False) -> JsonDocument:
    label = "JSONC" if kind is AdapterKind.JSONC else "JSON"
    text = decode_utf8(content, label)
    try:
        tokens = _lex(text, allow_comments=kind is AdapterKind.JSONC)
        semantic = _semantic_view(
            text,
            tokens,
            allow_extensions=kind is AdapterKind.JSONC,
        )
        root = _StructureParser(text, tokens).parse()
        if root.value != semantic:
            raise ValueError("lexical and semantic JSON views disagree")
    except _DuplicateObjectKey as exc:
        raise ControlPlaneError(f"{label} content contains a duplicate object key") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        noun = "fragment" if fragment else "content"
        detail = "a single JSON value" if fragment else f"valid {label}"
        raise ControlPlaneError(f"{noun} must contain {detail}") from exc
    return JsonDocument(text, root)


def _normalize_fragment_numbers(document: JsonDocument) -> str:
    """Apply Prettier's lexical number normalization inside an owned fragment."""
    edits = [
        (
            token.start,
            token.end,
            _prettier_number(document.text[token.start : token.end]),
        )
        for token in _lex(document.text, allow_comments=True)
        if token.kind == "number"
    ]
    return apply_edits(document.text, edits)


def container_value_without_comments(content: bytes, kind: AdapterKind) -> JsonValue | None:
    """Return container semantics only when deleting it cannot discard JSONC comments."""
    if kind not in {AdapterKind.JSON, AdapterKind.JSONC}:
        raise ControlPlaneError("JSON container inspection requires a JSON-family adapter")
    text = decode_utf8(content, kind.value.upper())
    try:
        tokens = _lex(text, allow_comments=kind is AdapterKind.JSONC)
    except ValueError as exc:
        raise ControlPlaneError("content is not valid JSON-family syntax") from exc
    if any(token.kind == "comment" for token in tokens):
        return None
    return _parse(content, kind).root.value


def _scope(kind: AdapterKind, value: str) -> ScopeSpec:
    try:
        normalized = normalize_scope(kind, value)
    except ValueError as exc:
        raise ControlPlaneError(f"{kind.value.upper()} scope is not canonical") from exc
    if normalized.startswith("key:"):
        return ScopeSpec(
            normalized,
            "key",
            decode_json_pointer(normalized.removeprefix("key:")),
        )
    if normalized.startswith("set:"):
        pointer, identity = normalized.removeprefix("set:").rsplit("#value=", 1)
        return ScopeSpec(
            normalized,
            "set",
            decode_json_pointer(pointer),
            identity=unquote(identity),
        )
    pointer, binding = normalized.removeprefix("keyed-set:").rsplit("#", 1)
    identity_key, identity = binding.split("=", 1)
    return ScopeSpec(
        normalized,
        "keyed-set",
        decode_json_pointer(pointer),
        identity_key=unquote(identity_key),
        identity=unquote(identity),
    )


def _object_member(node: JsonNode, key: str) -> tuple[int, JsonMember] | None:
    if node.kind != "object":
        return None
    matches = [(index, member) for index, member in enumerate(node.members) if member.key == key]
    if len(matches) > 1:
        raise ControlPlaneError("JSON content contains a duplicate object key")
    return matches[0] if matches else None


def _node_at(root: JsonNode, path: tuple[str, ...]) -> JsonNode | None:
    current = root
    for component in path:
        if current.kind == "object":
            found = _object_member(current, component)
            if found is None:
                return None
            current = found[1].value
            continue
        if current.kind == "array" and component.isdecimal():
            index = int(component)
            if index >= len(current.elements):
                return None
            current = current.elements[index]
            continue
        return None
    return current


def _scalar_identity(value: JsonValue, *, casefold: bool) -> str | None:
    if isinstance(value, (list, dict)):
        return None
    if isinstance(value, str):
        normalized = unicodedata.normalize("NFC", value)
        return normalized.casefold() if casefold else normalized
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _key_location(root: JsonNode, path: tuple[str, ...]) -> LocatedUnit | None:
    if not path:
        raise ControlPlaneError("JSON key scope must identify an object member")
    parent = _node_at(root, path[:-1])
    if parent is None:
        return None
    if parent.kind != "object":
        raise ControlPlaneError("JSON key scope parent is not an object")
    found = _object_member(parent, path[-1])
    if found is None:
        return None
    index, member = found
    return LocatedUnit(member.value, parent, index, member)


def _array_location(root: JsonNode, spec: ScopeSpec) -> LocatedUnit | None:
    container = _node_at(root, spec.path)
    if container is None:
        return None
    if container.kind != "array":
        raise ControlPlaneError("JSON set scope does not identify an array")
    matches: list[tuple[int, JsonNode]] = []
    seen: set[str] = set()
    for index, element in enumerate(container.elements):
        if spec.kind == "set":
            identity = _scalar_identity(element.value, casefold=True)
        else:
            identity = None
            if element.kind == "object" and spec.identity_key is not None:
                member = _object_member(element, spec.identity_key)
                if member is not None:
                    identity = _scalar_identity(member[1].value.value, casefold=False)
        if identity is None:
            continue
        if identity in seen:
            label = "set identity" if spec.kind == "set" else "keyed-set identity"
            raise ControlPlaneError(f"JSON content contains a duplicate {label}")
        seen.add(identity)
        wanted = spec.identity.casefold() if spec.kind == "set" and spec.identity else spec.identity
        if identity == wanted:
            matches.append((index, element))
    if not matches:
        return None
    index, node = matches[0]
    return LocatedUnit(node, container, index)


def _locate(root: JsonNode, spec: ScopeSpec) -> LocatedUnit | None:
    return _key_location(root, spec.path) if spec.kind == "key" else _array_location(root, spec)


def _unit(document: JsonDocument, spec: ScopeSpec) -> AdapterUnit | None:
    located = _locate(document.root, spec)
    if located is None:
        return None
    raw = document.text[located.node.start : located.node.end].encode()
    return AdapterUnit(
        spec.normalized,
        located.node.value,
        raw,
        semantic_digest(located.node.value),
    )


def _check_fragment_identity(spec: ScopeSpec, value: JsonValue) -> None:
    if spec.kind == "key":
        return
    if spec.kind == "set":
        identity = _scalar_identity(value, casefold=True)
        wanted = spec.identity.casefold() if spec.identity else spec.identity
    else:
        if not isinstance(value, dict) or spec.identity_key not in value:
            raise ControlPlaneError("JSON keyed-set fragment is missing its identity key")
        identity = _scalar_identity(value[spec.identity_key], casefold=False)
        wanted = spec.identity
    if identity != wanted:
        raise ControlPlaneError("JSON fragment does not match its declared identity")


def _check_declared_value(actual: JsonValue, declared: JsonValue | bytes | None) -> None:
    if declared is not None and (
        isinstance(declared, bytes) or semantic_digest(declared) != semantic_digest(actual)
    ):
        raise ControlPlaneError("JSON fragment does not match its declared semantic value")


def _semantically_equal(left: JsonValue, right: JsonValue) -> bool:
    return semantic_digest(left) == semantic_digest(right)


def _emptied_line_span(
    text: str,
    start: int,
    end: int,
    comma: JsonToken | None,
) -> tuple[int, int] | None:
    """Return the line span a removal would reduce to whitespace, when it exists.

    Deleting only the unit and its separator leaves the removed line's own
    indentation behind, which fails ``git diff --check`` and the Prettier gate
    (issue #78). The line is consumed only when nothing but whitespace would
    survive on it, so a shared line's comment or code keeps its bytes.
    """
    start_of_line = line_start(text, start)
    if text[start_of_line:start].strip():
        return None
    newline = text.find("\n", end)
    line_end = len(text) if newline == -1 else newline + 1
    trailing = (
        f"{text[end : comma.start]}{text[comma.end : line_end]}"
        if comma is not None and end <= comma.start and comma.end <= line_end
        else text[end:line_end]
    )
    if trailing.strip():
        return None
    return start_of_line, line_end


def _deletion_edits(
    located: LocatedUnit,
    text: str | None = None,
    *,
    prune_whitespace: bool = False,
) -> list[tuple[int, int, str]]:
    # Delete the semantic code and its separator as disjoint spans. Comments
    # and whitespace between them are consumer bytes and must survive removal.
    if located.member is not None:
        start = located.member.key_token.start
        end = located.member.value.end
        comma = located.member.comma
        previous_comma = (
            located.container.members[located.index - 1].comma if located.index > 0 else None
        )
    else:
        start = located.node.start
        end = located.node.end
        comma = located.container.commas[located.index]
        previous_comma = located.container.commas[located.index - 1] if located.index > 0 else None
    if prune_whitespace and text is not None:
        count = (
            len(located.container.members)
            if located.container.kind == "object"
            else len(located.container.elements)
        )
        if comma is not None and located.index + 1 < count:
            next_start = (
                located.container.members[located.index + 1].key_token.start
                if located.container.kind == "object"
                else located.container.elements[located.index + 1].start
            )
            separator = text[end:next_start]
            if separator.replace(",", "", 1).strip() == "":
                return [(start, next_start, "")]
        if previous_comma is not None:
            separator = text[previous_comma.start : start]
            if separator.replace(",", "", 1).strip() == "":
                return [(previous_comma.start, end, "")]
    edits = [(start, end, "")]
    selected_comma = comma if comma is not None else previous_comma
    if selected_comma is not None:
        edits.append((selected_comma.start, selected_comma.end, ""))
    if text is None:
        return edits
    emptied = _emptied_line_span(text, start, end, selected_comma)
    if emptied is None:
        return edits
    line_start, line_end = emptied
    edits = [(line_start, line_end, "")]
    # A separator that closes the previous line (last-unit removal) sits outside
    # the consumed line and still needs its own disjoint span.
    if selected_comma is not None and not (
        line_start <= selected_comma.start and selected_comma.end <= line_end
    ):
        edits.append((selected_comma.start, selected_comma.end, ""))
    return edits


def _prune_empty_object_ancestors(
    content: bytes,
    kind: AdapterKind,
    path: tuple[str, ...],
) -> bytes:
    """Remove empty parent objects known to originate in a platform-created file."""
    parent = path[:-1]
    while parent:
        document = _parse(content, kind)
        node = _node_at(document.root, parent)
        if node is None or node.kind != "object" or node.value != {}:
            break
        raw = document.text[node.start : node.end].encode()
        if container_value_without_comments(raw, kind) != {}:
            break
        located = _key_location(document.root, parent)
        if located is None:
            break
        content = apply_edits(
            document.text,
            _deletion_edits(located, document.text, prune_whitespace=True),
        ).encode()
        parent = parent[:-1]
    return content


def _item_start(container: JsonNode, index: int) -> int:
    if container.kind == "object":
        return container.members[index].key_token.start
    return container.elements[index].start


def _item_end(container: JsonNode, index: int) -> int:
    if container.kind == "object":
        return container.members[index].value.end
    return container.elements[index].end


def _item_comma(container: JsonNode, index: int) -> JsonToken | None:
    if container.kind == "object":
        return container.members[index].comma
    return container.commas[index]


def _container_nodes(node: JsonNode) -> tuple[JsonNode, ...]:
    descendants: list[JsonNode] = []
    if node.kind in {"object", "array"}:
        descendants.append(node)
    if node.kind == "object":
        for member in node.members:
            descendants.extend(_container_nodes(member.value))
    elif node.kind == "array":
        for element in node.elements:
            descendants.extend(_container_nodes(element))
    return tuple(descendants)


def _layout(document: JsonDocument) -> JsonLayout:
    newline = preferred_newline(document.text)
    for container in _container_nodes(document.root):
        if container.opening is None or container.closing is None:
            continue
        body = document.text[container.opening.end : container.closing.start]
        if "\n" not in body:
            continue
        closing_line = line_start(document.text, container.closing.start)
        closing_indent = document.text[closing_line : container.closing.start]
        if closing_indent.strip():
            continue
        count = len(container.members) if container.kind == "object" else len(container.elements)
        starts = tuple(_item_start(container, index) for index in range(count))
        for start in starts:
            line = line_start(document.text, start)
            child_indent = document.text[line:start]
            if (
                not child_indent.strip()
                and child_indent.startswith(closing_indent)
                and child_indent != closing_indent
            ):
                return JsonLayout(newline, child_indent[len(closing_indent) :])
        for line in body.splitlines():
            indentation = line[: len(line) - len(line.lstrip(" \t"))]
            if (
                line.strip()
                and indentation.startswith(closing_indent)
                and indentation != closing_indent
            ):
                return JsonLayout(newline, indentation[len(closing_indent) :])
    return JsonLayout(newline, "\t")


def _node_location(
    root: JsonNode,
    target: JsonNode,
    depth: int = 0,
) -> tuple[LocatedUnit, int] | None:
    if root.kind == "object":
        for index, member in enumerate(root.members):
            if member.value is target:
                return LocatedUnit(target, root, index, member), depth + 1
            found = _node_location(member.value, target, depth + 1)
            if found is not None:
                return found
    elif root.kind == "array":
        for index, element in enumerate(root.elements):
            if element is target:
                return LocatedUnit(target, root, index), depth + 1
            found = _node_location(element, target, depth + 1)
            if found is not None:
                return found
    return None


def _located_layout(
    document: JsonDocument,
    located: LocatedUnit,
    layout: JsonLayout,
) -> tuple[str, int]:
    start = located.member.key_token.start if located.member is not None else located.node.start
    line = line_start(document.text, start)
    line_prefix = document.text[line:start]
    if not line_prefix.strip():
        indent = line_prefix
    else:
        if located.container is document.root:
            container_depth = 0
        else:
            container_location = _node_location(document.root, located.container)
            if container_location is None:
                raise ControlPlaneError("JSON insertion target is outside the parsed document")
            container_depth = container_location[1]
        indent = layout.indent_unit * (container_depth + 1)
    if located.member is not None:
        key = document.text[located.member.key_token.start : located.member.key_token.end]
        prefix_width = _prettier_width(key) + 2 + (1 if located.member.comma is not None else 0)
    else:
        comma = located.container.commas[located.index]
        prefix_width = 1 if comma is not None else 0
    return indent, prefix_width


def _node_layout(
    document: JsonDocument,
    node: JsonNode,
    layout: JsonLayout,
) -> tuple[str, int]:
    if node is document.root:
        return "", 0
    location = _node_location(document.root, node)
    if location is None:
        raise ControlPlaneError("JSON node is outside the parsed document")
    return _located_layout(document, location[0], layout)


def _flat_preserving(node: JsonNode, text: str) -> str:
    if node.kind == "scalar":
        return text[node.start : node.end]
    if node.kind == "object":
        if not node.members:
            return "{}"
        members = (
            (
                f"{text[member.key_token.start : member.key_token.end]}: "
                f"{_flat_preserving(member.value, text)}"
            )
            for member in node.members
        )
        return f"{{ {', '.join(members)} }}"
    return f"[{', '.join(_flat_preserving(element, text) for element in node.elements)}]"


def _render_preserving(
    node: JsonNode,
    text: str,
    layout: JsonLayout,
    indent: str = "",
    *,
    prefix_width: int = 0,
) -> str:
    """Render layout while retaining every validated key and scalar token."""
    if node.kind == "scalar":
        return text[node.start : node.end]
    flat = _flat_preserving(node, text)
    if not _forces_prettier_break(node.value) and _fits_prettier_line(indent, prefix_width, flat):
        return flat
    child_indent = f"{indent}{layout.indent_unit}"
    if node.kind == "object":
        members: list[str] = []
        for index, member in enumerate(node.members):
            key = text[member.key_token.start : member.key_token.end]
            value = _render_preserving(
                member.value,
                text,
                layout,
                child_indent,
                prefix_width=(
                    _prettier_width(key) + 2 + (1 if index < len(node.members) - 1 else 0)
                ),
            )
            members.append(f"{child_indent}{key}: {value}")
        return (
            f"{{{layout.newline}"
            + f",{layout.newline}".join(members)
            + f"{layout.newline}{indent}}}"
        )
    elements: list[str] = []
    for index, element in enumerate(node.elements):
        rendered = _render_preserving(
            element,
            text,
            layout,
            child_indent,
            prefix_width=(1 if index < len(node.elements) - 1 else 0),
        )
        elements.append(f"{child_indent}{rendered}")
    return f"[{layout.newline}" + f",{layout.newline}".join(elements) + f"{layout.newline}{indent}]"


def _has_comments(document: JsonDocument) -> bool:
    return any(token.kind == "comment" for token in _lex(document.text, allow_comments=True))


def _is_clean_container(
    document: JsonDocument,
    node: JsonNode,
    layout: JsonLayout,
) -> bool:
    if any(
        token.kind == "comment" and node.start <= token.start < node.end
        for token in _lex(document.text, allow_comments=True)
    ):
        return False
    indent, prefix_width = _node_layout(document, node, layout)
    expected = _render_preserving(
        node,
        document.text,
        layout,
        indent=indent,
        prefix_width=prefix_width,
    )
    return document.text[node.start : node.end] == expected


def _mutation_container_path(spec: ScopeSpec) -> tuple[str, ...]:
    return spec.path[:-1] if spec.kind == "key" else spec.path


def _clean_mutation_container_path(
    document: JsonDocument,
    spec: ScopeSpec,
    layout: JsonLayout,
) -> tuple[str, ...] | None:
    if not _has_comments(document):
        expected = _render_preserving(document.root, document.text, layout)
        if document.text != f"{expected}{layout.newline}":
            return None
        return ()
    path = _mutation_container_path(spec)
    for length in range(len(path) + 1):
        candidate = path[:length]
        container = _node_at(document.root, candidate)
        if container is None:
            break
        if container.kind in {"object", "array"} and _is_clean_container(
            document,
            container,
            layout,
        ):
            return candidate
    if _node_at(document.root, path) is None:
        return path
    return None


def _finish_owned_mutation(
    document: JsonDocument,
    spec: ScopeSpec,
    layout: JsonLayout,
    *,
    clean_container_path: tuple[str, ...] | None,
) -> str:
    """Format the owned value, reflowing ancestors only in a clean context."""
    located = _locate(document.root, spec)
    if located is None:
        raise ControlPlaneError("JSON mutation did not materialize its declared scope")
    if clean_container_path is not None:
        container = _node_at(document.root, clean_container_path)
        if container is None or container.kind not in {"object", "array"}:
            raise ControlPlaneError("JSON mutation did not materialize its containing scope")
        indent, prefix_width = _node_layout(document, container, layout)
        formatted = _render_preserving(
            container,
            document.text,
            layout,
            indent,
            prefix_width=prefix_width,
        )
        return apply_edits(
            document.text,
            [(container.start, container.end, formatted)],
        )
    indent, prefix_width = _located_layout(document, located, layout)
    formatted = _render_preserving(
        located.node,
        document.text,
        layout,
        indent,
        prefix_width=prefix_width,
    )
    return apply_edits(
        document.text,
        [(located.node.start, located.node.end, formatted)],
    )


def _append(
    container: JsonNode,
    text: str,
    fragment: str,
    layout: JsonLayout,
) -> str:
    if container.opening is None or container.closing is None:
        raise ControlPlaneError("JSON insertion target has no bounded container")
    count = len(container.members) if container.kind == "object" else len(container.elements)
    newline = layout.newline
    fragment = fragment.replace("\r\n", "\n").replace("\n", newline)
    body = text[container.opening.end : container.closing.start]
    if "\n" not in body:
        if count == 0:
            return apply_edits(text, [(container.opening.end, container.opening.end, fragment)])
        last_comma = _item_comma(container, count - 1)
        if last_comma is not None:
            insertion = f" {fragment},"
            return apply_edits(text, [(last_comma.end, last_comma.end, insertion)])
        end = _item_end(container, count - 1)
        return apply_edits(text, [(end, end, f", {fragment}")])

    closing_line = line_start(text, container.closing.start)
    closing_indent = text[closing_line : container.closing.start]
    if closing_indent.strip():
        raise ControlPlaneError("JSON closing delimiter is not independently addressable")
    if count:
        first_start = _item_start(container, 0)
        first_line = line_start(text, first_start)
        child_indent = text[first_line:first_start]
        if child_indent.strip():
            child_indent = f"{closing_indent}{layout.indent_unit}"
    else:
        child_indent = f"{closing_indent}{layout.indent_unit}"
    indented = fragment.replace(newline, f"{newline}{child_indent}")
    edits: list[tuple[int, int, str]] = [
        (closing_line, closing_line, f"{child_indent}{indented}"),
    ]
    # Match the existing container's trailing-comma style; changing that style
    # would rewrite consumer formatting outside the newly inserted unit.
    trailing = count > 0 and _item_comma(container, count - 1) is not None
    if trailing:
        edits[0] = (closing_line, closing_line, f"{child_indent}{indented},{newline}")
    elif count:
        end = _item_end(container, count - 1)
        edits.append((end, end, ","))
        edits[0] = (closing_line, closing_line, f"{child_indent}{indented}{newline}")
    else:
        edits[0] = (closing_line, closing_line, f"{child_indent}{indented}{newline}")
    return apply_edits(text, edits)


class _JsonFamilyAdapter:
    """Compose selected JSON-family units through exact lexical splices."""

    kind: AdapterKind

    def inspect(self, content: bytes, scopes: tuple[str, ...]) -> AdapterState:
        document = _parse(content, self.kind)
        specs = [_scope(self.kind, scope) for scope in scopes]
        normalized = [spec.normalized for spec in specs]
        if len(normalized) != len(set(normalized)):
            raise ControlPlaneError("JSON inspection contains a duplicate scope")
        units = [
            unit
            for spec in sorted(specs, key=lambda item: item.normalized.encode("utf-8"))
            if (unit := _unit(document, spec)) is not None
        ]
        return AdapterState(content, tuple(units))

    def render(self, state: AdapterState, changes: tuple[UnitChange, ...]) -> bytes:
        specs = [(change, _scope(self.kind, change.scope)) for change in changes]
        normalized = [spec.normalized for _, spec in specs]
        if len(normalized) != len(set(normalized)):
            raise ControlPlaneError("JSON rendering contains a duplicate change scope")
        content = state.content
        for change, spec in sorted(specs, key=lambda item: item[1].normalized.encode("utf-8")):
            document = _parse(content, self.kind)
            located = _locate(document.root, spec)
            if change.kind in {ActionKind.NOOP, ActionKind.PRESERVE}:
                if change.content is not None or change.value is not None:
                    raise ControlPlaneError("non-mutating JSON change cannot carry content")
                continue
            if change.kind is ActionKind.REMOVE:
                if change.content is not None or change.value is not None:
                    raise ControlPlaneError("JSON removal cannot carry content")
                if located is None:
                    raise ControlPlaneError("JSON removal scope is not present")
                content = apply_edits(
                    document.text,
                    _deletion_edits(
                        located,
                        document.text,
                        prune_whitespace=change.prune_empty_ancestors,
                    ),
                ).encode()
                if change.prune_empty_ancestors and spec.kind == "key":
                    content = _prune_empty_object_ancestors(content, self.kind, spec.path)
                _parse(content, self.kind)
                continue
            if change.content is None:
                raise ControlPlaneError("mutating JSON change requires a bounded fragment")
            fragment_document = _parse(change.content, self.kind, fragment=True)
            desired = fragment_document.root.value
            fragment = _normalize_fragment_numbers(fragment_document)
            _check_declared_value(desired, change.value)
            _check_fragment_identity(spec, desired)
            if change.kind is ActionKind.ADOPT:
                if located is None or not _semantically_equal(located.node.value, desired):
                    raise ControlPlaneError("JSON adoption requires an equal existing value")
                continue
            if change.kind is ActionKind.CREATE:
                if located is not None:
                    raise ControlPlaneError("JSON creation scope already exists")
                layout = _layout(document)
                clean_container_path = _clean_mutation_container_path(
                    document,
                    spec,
                    layout,
                )
                created = self._create(document, spec, fragment, layout)
                created_document = _parse(created.encode(), self.kind)
                content = _finish_owned_mutation(
                    created_document,
                    spec,
                    layout,
                    clean_container_path=clean_container_path,
                ).encode()
                _parse(content, self.kind)
                continue
            if change.kind is not ActionKind.UPDATE:
                raise ControlPlaneError("JSON adapter received an unsupported action")
            if located is None:
                raise ControlPlaneError("JSON update scope is not present")
            if _semantically_equal(located.node.value, desired):
                continue
            layout = _layout(document)
            clean_container_path = _clean_mutation_container_path(
                document,
                spec,
                layout,
            )
            updated = apply_edits(
                document.text,
                [(located.node.start, located.node.end, fragment)],
            )
            updated_document = _parse(updated.encode(), self.kind)
            content = _finish_owned_mutation(
                updated_document,
                spec,
                layout,
                clean_container_path=clean_container_path,
            ).encode()
            _parse(content, self.kind)
        return content

    def _create(
        self,
        document: JsonDocument,
        spec: ScopeSpec,
        fragment: str,
        layout: JsonLayout,
    ) -> str:
        if spec.kind == "key":
            if not spec.path:
                raise ControlPlaneError("JSON key scope must identify an object member")
            parent = _node_at(document.root, spec.path[:-1])
            if parent is None:
                grandparent = _node_at(document.root, spec.path[:-2])
                if grandparent is None:
                    raise ControlPlaneError("JSON creation parent scope is not present")
                if grandparent.kind != "object":
                    raise ControlPlaneError("JSON creation parent is not an object")
                parent_key = json.dumps(spec.path[-2], ensure_ascii=False)
                member_key = json.dumps(spec.path[-1], ensure_ascii=False)
                return _append(
                    grandparent,
                    document.text,
                    f"{parent_key}: {{{member_key}: {fragment}}}",
                    layout,
                )
            if parent.kind != "object":
                raise ControlPlaneError("JSON creation parent is not an object")
            member = f"{json.dumps(spec.path[-1], ensure_ascii=False)}: {fragment}"
            return _append(parent, document.text, member, layout)
        container = _node_at(document.root, spec.path)
        if container is None:
            if not spec.path:
                raise ControlPlaneError("JSON set container is not present")
            parent = _node_at(document.root, spec.path[:-1])
            if parent is None:
                if spec.kind != "keyed-set":
                    raise ControlPlaneError("JSON set container parent is not present")
                grandparent = _node_at(document.root, spec.path[:-2])
                if grandparent is None:
                    raise ControlPlaneError("JSON set container parent is not present")
                if grandparent.kind != "object":
                    raise ControlPlaneError("JSON set container grandparent is not an object")
                parent_key = json.dumps(spec.path[-2], ensure_ascii=False)
                member_key = json.dumps(spec.path[-1], ensure_ascii=False)
                return _append(
                    grandparent,
                    document.text,
                    f"{parent_key}: {{{member_key}: [{fragment}]}}",
                    layout,
                )
            if parent.kind != "object":
                raise ControlPlaneError("JSON set container parent is not an object")
            member = f"{json.dumps(spec.path[-1], ensure_ascii=False)}: [{fragment}]"
            return _append(parent, document.text, member, layout)
        if container.kind != "array":
            raise ControlPlaneError("JSON set scope does not identify an array")
        return _append(container, document.text, fragment, layout)


class JsonAdapter(_JsonFamilyAdapter):
    """Compose strict JSON semantic units without reserializing the document."""

    kind = AdapterKind.JSON


class JsoncAdapter(_JsonFamilyAdapter):
    """Compose comment- and trailing-comma-tolerant JSONC semantic units."""

    kind = AdapterKind.JSONC
