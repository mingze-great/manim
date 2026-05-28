import argparse
import json
import subprocess
import sys
import time
import urllib.request


TRANSIENT_PATTERNS = (
    "connection was reset",
    "connection reset",
    "could not connect to server",
    "empty reply from server",
    "failed to connect",
    "gnutls recv error",
    "non-properly terminated",
    "operation timed out",
    "timed out",
    "recv failure",
    "http/2 stream",
    "remote end hung up unexpectedly",
    "unexpected eof",
    "early eof",
    "connection died",
    "could not resolve host",
    "could not resolve hostname",
)


GITHUB_DOH_URL = "https://dns.google/resolve?name=github.com&type=A"


def is_transient_failure(output: str) -> bool:
    lowered = output.lower()
    return any(pattern in lowered for pattern in TRANSIENT_PATTERNS)


def get_windows_ssl_backend() -> str | None:
    try:
        result = subprocess.run(
            ["git", "config", "--get", "http.sslBackend"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None

    backend = result.stdout.strip()
    if backend == "openssl" and sys.platform.startswith("win"):
        return "schannel"
    return None


def resolve_github_ip(timeout: int = 10) -> str | None:
    try:
        request = urllib.request.Request(
            GITHUB_DOH_URL,
            headers={"Accept": "application/dns-json", "User-Agent": "git-retry"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    for answer in payload.get("Answer", []):
        if answer.get("type") == 1 and answer.get("data"):
            return answer["data"]
    return None


def build_command(args: argparse.Namespace) -> list[str]:
    command = ["git"]
    if args.github_https_workaround:
        ssl_backend = get_windows_ssl_backend()
        if ssl_backend:
            command.extend(["-c", f"http.sslBackend={ssl_backend}"])

        command.extend([
            "-c",
            "http.version=HTTP/1.1",
            "-c",
            "http.maxRequests=1",
        ])

        if args.resolve_github:
            github_ip = args.github_ip or resolve_github_ip()
            if github_ip:
                command.extend(["-c", f"http.curloptResolve=github.com:443:{github_ip}"])

    command.extend(args.git_args)
    return command


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run git with retry/backoff for transient GitHub HTTPS failures."
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--retry-delay", type=int, default=5)
    parser.add_argument("--github-https-workaround", action="store_true", default=True)
    parser.add_argument("--resolve-github", action="store_true")
    parser.add_argument("--github-ip")
    parser.add_argument("git_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if not args.git_args:
        parser.error("missing git arguments")

    if args.git_args[0] == "--":
        args.git_args = args.git_args[1:]

    command = build_command(args)
    last_result = None
    for attempt in range(1, args.retries + 1):
        result = subprocess.run(command, cwd=args.repo, capture_output=True)
        last_result = result
        sys.stdout.buffer.write(result.stdout)
        sys.stderr.buffer.write(result.stderr)
        if result.returncode == 0:
            return 0

        combined_output = b"\n".join([result.stdout, result.stderr]).decode("utf-8", errors="replace")
        if attempt == args.retries or not is_transient_failure(combined_output):
            return result.returncode

        print(
            f"git_retry attempt {attempt}/{args.retries} hit transient transport failure; retrying in {args.retry_delay}s",
            file=sys.stderr,
        )
        time.sleep(args.retry_delay)

    return 1 if last_result is None else last_result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
