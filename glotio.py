# -*- coding: utf-8 -*-
"""
glotio.py — glot.io SDK 的自托管替代 (兼容层)

背景:
    glot.io 已停止 API 服务。本文件实现与原 glotio SDK 完全相同的
    Runner 接口, 但请求发往自建的 Piston 服务 (部署在 26号机)。

用法 (与原代码完全一致, 平台代码零修改):
    from glotio import Runner
    g = Runner("")                       # token 参数保留但被忽略
    g.set_lang("python")
    g.set_code("print('hi')", filename="main.py")
    g.set_stdin("input text")
    g.set_command("python3 main.py 'my arg'")
    result = g.run()
    print(result["stdout"], result["stderr"])

接入方式 (二选一):
    1) 环境变量:  export PISTON_URL=http://<26号机IP>:2000
    2) 代码内:    Runner("", base_url="http://<26号机IP>:2000")

把本文件放到平台项目的 import 路径下即可 (优先级高于 pip 装的旧包,
建议 pip uninstall glotio 避免歧义)。
"""
import json
import os
import re
import shlex
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:2000"

# The configured runners are private IP endpoints.  A desktop HTTP proxy can
# return a misleading 502 before the request reaches the runner, so execution
# traffic uses a direct opener and never follows HTTP(S)_PROXY for these URLs.
_DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

# glot 语言名 -> Piston 语言名
_LANG_ALIAS = {
    "python": "python",
    "python3": "python",
    "python2": "python2",
    "javascript": "javascript",
    "nodejs": "javascript",
    "node": "javascript",
    "c": "c",
    "cpp": "c++",
    "c++": "c++",
    "c++17": "c++",
    "java": "java",
    "go": "go",
    "rust": "rust",
    "ruby": "ruby",
    "php": "php",
    "bash": "bash",
    "sh": "bash",
    "shell": "bash",
    "kotlin": "kotlin",
    "swift": "swift",
    "c#": "c#",
    "csharp": "c#",
}


class _GlotResult(dict):
    """兼容 dict 访问和属性访问两种风格: r["stdout"] / r.stdout"""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


class Runner(object):
    def __init__(self, token=None, base_url=None, timeout=60):
        """
        token:    兼容原 SDK 的参数, 自建服务不校验, 传任意值均可
        base_url: Piston 服务地址, 默认取环境变量 PISTON_URL
        timeout:  单次运行超时秒数
        """
        self.base_url = (base_url or os.environ.get("PISTON_URL") or DEFAULT_BASE).rstrip("/")
        self.token = token
        self.lang = None
        self.files = []
        self.stdin = ""
        self.command = None
        self.version = None
        self.timeout = timeout
        self._runtime_cache = None  # (语言, 版本) 缓存

    # ---------- 与原 glotio SDK 相同的接口 ----------
    def set_lang(self, lang):
        self.lang = lang
        self._runtime_cache = None

    def set_version(self, version):
        self.version = version
        self._runtime_cache = None

    def set_code(self, code, filename="main.py"):
        self.files = [{"name": filename, "content": code}]

    def set_files(self, files):
        """扩展接口: 多文件支持, files=[{"name":..,"content":..}, ..]"""
        self.files = files

    def set_stdin(self, stdin):
        self.stdin = stdin or ""

    def set_command(self, command):
        self.command = command

    # ---------- 内部实现 ----------
    def _resolve_runtime(self):
        """查询 Piston 已安装运行时, 把 glot 语言名解析成 (piston语言, 具体版本)"""
        if self._runtime_cache:
            return self._runtime_cache
        if not self.lang:
            raise RuntimeError("请先调用 set_lang()")

        url = self.base_url + "/api/v2/runtimes"
        with _DIRECT_OPENER.open(url, timeout=10) as resp:
            runtimes = json.load(resp)

        want = self.lang.strip().lower()
        piston_name = _LANG_ALIAS.get(want, want)

        def _ver_key(v):
            return [int(x) if x.isdigit() else 0 for x in re.split(r"[.\-+]", v)]

        candidates = [
            r for r in runtimes
            if r.get("language") == piston_name
            or piston_name in (r.get("aliases") or [])
        ]
        if not candidates:
            installed = sorted(set(r["language"] for r in runtimes))
            raise RuntimeError(
                "Piston 上未安装语言 %r (原语言名 %r)。已安装: %s。"
                "可在26号机上执行: docker exec piston_api ppman install %s"
                % (piston_name, self.lang, ", ".join(installed), piston_name)
            )
        requested = str(self.version or "").strip()
        exact = [r for r in candidates if requested and r.get("version") == requested]
        best = (exact[0] if exact else max(candidates, key=lambda r: _ver_key(r["version"])))
        self._runtime_cache = (best["language"], best["version"])
        return self._runtime_cache

    def _parse_command_args(self):
        """把 glot 的 command (如 "python3 main.py 'my arg'") 解析成 Piston 的 args"""
        if not self.command:
            return []
        try:
            parts = shlex.split(self.command)
        except ValueError:
            parts = self.command.split()
        fname = self.files[0]["name"] if self.files else ""
        for i, p in enumerate(parts):
            if p == fname or p.endswith("/" + fname):
                return parts[i + 1:]
        return []

    def _post_execute(self, payload, http_timeout):
        req = urllib.request.Request(
            self.base_url + "/api/v2/execute",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with _DIRECT_OPENER.open(req, timeout=http_timeout) as resp:
            return json.load(resp)

    @staticmethod
    def _url_error(e):
        return _GlotResult({
            "stdout": "",
            "stderr": "",
            "error": "无法连接执行服务: %s" % (e.reason,),
            "executionTime": 0,
        })

    def run(self, timeout=None):
        """执行代码, 返回 glot 风格结果 dict:
        {"stdout":..., "stderr":..., "error":..., "executionTime": 毫秒}

        注: 实际运行时长受服务器端 PISTON_RUN_TIMEOUT 限制,
            若请求的超时超过服务器上限, 会自动夹紧到上限后重试。
        """
        if not self.files:
            raise RuntimeError("请先调用 set_code()")
        timeout = timeout or self.timeout
        language, version = self._resolve_runtime()

        payload = {
            "language": language,
            "version": version,
            "files": self.files,
            "stdin": self.stdin,
            "args": self._parse_command_args(),
            "compile_timeout": 10000,
            "run_timeout": int(timeout * 1000),
        }

        t0 = time.time()
        try:
            data = self._post_execute(payload, timeout + 30)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            # 400 且是"超时参数超限": 解析出服务器上限, 夹紧后重试一次
            m = re.search(
                r"(\w+) cannot exceed the configured limit of (\d+)", body)
            if e.code == 400 and m and m.group(1) in payload:
                payload[m.group(1)] = min(payload[m.group(1)], int(m.group(2)))
                try:
                    data = self._post_execute(payload, timeout + 30)
                except urllib.error.HTTPError as e2:
                    body2 = e2.read().decode("utf-8", errors="replace")
                    return _GlotResult({
                        "stdout": "",
                        "stderr": "",
                        "error": "执行服务返回 HTTP %d: %s" % (e2.code, body2[:2000]),
                        "executionTime": 0,
                    })
                except urllib.error.URLError as e2:
                    return self._url_error(e2)
            else:
                return _GlotResult({
                    "stdout": "",
                    "stderr": "",
                    "error": "执行服务返回 HTTP %d: %s" % (e.code, body[:2000]),
                    "executionTime": 0,
                })
        except urllib.error.URLError as e:
            return self._url_error(e)

        elapsed_ms = int((time.time() - t0) * 1000)
        run_info = data.get("run") or {}
        compile_info = data.get("compile") or {}

        stdout = run_info.get("stdout", "")
        stderr = run_info.get("stderr", "")
        error = ""

        # 编译型语言: 编译错误放 error 字段 (与 glot 行为一致)
        if compile_info.get("code") not in (None, 0):
            error = (compile_info.get("stderr") or "").strip()
        # 服务级错误 (如语言未安装)
        if not error and data.get("message"):
            error = str(data["message"])

        return _GlotResult({
            "stdout": stdout,
            "stderr": stderr,
            "error": error,
            "executionTime": elapsed_ms,
            # 附加信息 (glot 没有但很有用, 不影响兼容性)
            "exitCode": run_info.get("code"),
            "language": data.get("language", language),
            "version": data.get("version", version),
        })


# ---------- 直接运行本文件可做自检 ----------
if __name__ == "__main__":
    g = Runner(os.environ.get("GLOTIO_TOKEN", ""))
    g.set_lang("python")
    g.set_code(
        "import sys\n"
        "print('Hello from Piston!')\n"
        "print('stdin:', sys.stdin.readline().strip())\n"
        "print('argv:', sys.argv[1:])\n",
        filename="main.py",
    )
    g.set_stdin("input text")
    g.set_command("python3 main.py 'my arg'")
    result = g.run()
    print("stdout:", result["stdout"])
    print("stderr:", result["stderr"])
    print("error :", result["error"])
    print("time  :", result["executionTime"], "ms")
